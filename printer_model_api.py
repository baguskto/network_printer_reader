from flask import Flask, request, jsonify
from pysnmp.hlapi import *
import socket
import re
import subprocess
import platform
import ipaddress

app = Flask(__name__)

def is_private_ip(ip):
    """Check if IP address is private/local network"""
    try:
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj.is_private
    except:
        return False

def ping_host(ip):
    """Test basic connectivity using ping"""
    try:
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "1", ip]
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False

def test_snmp_port(ip):
    """Test if SNMP port 161 is accessible"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)  # Reduced from 2 to 1 second
        result = sock.connect_ex((ip, 161))
        sock.close()
        return result == 0
    except:
        return False

def map_epson_model(model_code):
    """Map Epson internal codes to user-friendly model names"""
    epson_mapping = {
        'UB-E04': 'EPSON TM-U220IIB',
        'UB-E03': 'EPSON TM-U220IIIB', 
        'UB-U02': 'EPSON TM-U220II',
        'UB-U03': 'EPSON TM-U220III',
        'TM-T82X': 'EPSON TM-T82X',
        'TM-T88': 'EPSON TM-T88',
        'TM-T20': 'EPSON TM-T20',
        'TM-T70': 'EPSON TM-T70',
        'TM-T82': 'EPSON TM-T82',
        'TM-U950': 'EPSON TM-U950',
        'TM-U325': 'EPSON TM-U325',
        'TM-L90': 'EPSON TM-L90',
        'TM-P20': 'EPSON TM-P20',
        'TM-P60': 'EPSON TM-P60',
        'TM-P80': 'EPSON TM-P80'
    }
    
    # First clean up the input
    cleaned_code = model_code.strip()
    
    # Check if it's an exact match
    if cleaned_code in epson_mapping:
        return epson_mapping[cleaned_code]
    
    # Check if it contains any of the codes (partial matching)
    for code, full_name in epson_mapping.items():
        if code.upper() in cleaned_code.upper():
            return full_name
    
    # Special handling for specific patterns
    cleaned_upper = cleaned_code.upper()
    
    # Handle cases where EPSON prefix might be missing
    if any(tm_model in cleaned_upper for tm_model in ['TM-U220IIB', 'TM-T82X']):
        if not cleaned_upper.startswith('EPSON'):
            return 'EPSON ' + cleaned_code
    
    # If it already has EPSON prefix and looks like a model, keep it
    if cleaned_upper.startswith('EPSON') and ('TM-' in cleaned_upper or 'L-' in cleaned_upper):
        return cleaned_code
    
    return model_code  # Return original if no mapping found

def get_printer_model(ip):
    """Get printer model using SNMP with multiple community strings and OIDs"""
    try:
        # Try different community strings - prioritize most common ones
        community_strings = ['public', 'private']  # Reduced for faster response
        
        # Improved OID priority - Epson specific OIDs first, then generic ones
        oids_to_try = [
            # Epson-specific OIDs (highest priority for accurate model detection)
            '1.3.6.1.4.1.1248.1.2.2.1.1.1.1',      # Epson specific model name
            '1.3.6.1.4.1.1248.1.2.2.44.1.1.2.1',   # Epson printer model (from epson_print_conf)
            '1.3.6.1.4.1.1248.1.1.1.1.1.4.1.2',    # Another Epson model OID
            '1.3.6.1.2.1.25.3.2.1.3.1',            # hrDeviceDescr (device description)
            '1.3.6.1.2.1.1.1.0',                   # sysDescr (standard but can be generic)
        ]
        
        all_results = []  # Collect all valid results
        
        for community in community_strings:
            early_exit = False
            for oid in oids_to_try:
                try:
                    # Perform SNMP GET with pysnmp-lextudio (synchronous)
                    iterator = getCmd(
                        SnmpEngine(),
                        CommunityData(community, mpModel=0),
                        UdpTransportTarget((ip, 161), timeout=2, retries=1),
                        ContextData(),
                        ObjectType(ObjectIdentifier(oid))
                    )

                    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
                    
                    if not errorIndication and not errorStatus:
                        result = str(varBinds[0][1])
                        if result and result != 'No Such Object currently exists at this OID' and result != 'No Such Instance currently exists at this OID':
                            # Clean up the result
                            result = result.strip()
                            
                            if len(result) > 3:  # Valid response
                                all_results.append({
                                    'raw': result,
                                    'method': f"pysnmp-lextudio - community: {community}, OID: {oid}",
                                    'oid': oid,
                                    'priority': get_oid_priority(oid, result)
                                })
                                
                                # Early exit if we get excellent result from Epson-specific OID
                                if ('1.3.6.1.4.1.1248' in oid and ('TM-' in result.upper() or 'EPSON' in result.upper())):
                                    early_exit = True
                                    break
                except Exception as e:
                    continue
            
            if early_exit:
                break
        
        # Process results to find the best model name
        if all_results:
            # Sort by priority (higher priority first)
            all_results.sort(key=lambda x: x.get('priority', 0), reverse=True)
            
            # Priority 1: Look for results with actual printer model names (not generic descriptions)
            for res in all_results:
                cleaned = res['raw']
                # Skip generic print server descriptions
                if any(generic in cleaned.upper() for generic in [
                    'PRINT SERVER', 'ETHERNET', 'BUILT-IN', '11B/G/N', '10/100'
                ]):
                    continue
                    
                # Look for actual model names
                if any(model in cleaned.upper() for model in [
                    'TM-U220IIB', 'TM-U220', 'TM-T82X', 'TM-T88', 'TM-T20', 'TM-T70', 'TM-T82',
                    'TM-U950', 'TM-U325', 'TM-L90', 'TM-P20', 'TM-P60', 'TM-P80', 'UB-E04', 'UB-E03'
                ]):
                    # Apply Epson mapping if needed
                    mapped_result = map_epson_model(cleaned)
                    return mapped_result, res['method'] + (" (mapped)" if mapped_result != cleaned else "")
            
            # Priority 2: Look for Epson-specific OID results and try mapping
            for res in all_results:
                if '1.3.6.1.4.1.1248' in res['oid']:  # Epson-specific OID
                    cleaned = res['raw']
                    # Apply Epson mapping
                    mapped_result = map_epson_model(cleaned)
                    if mapped_result != cleaned:  # Mapping was successful
                        return mapped_result, res['method'] + " (mapped)"
                    # Even if no mapping, if it's from Epson OID and not generic, use it
                    if not any(generic in cleaned.upper() for generic in [
                        'PRINT SERVER', 'ETHERNET', 'BUILT-IN', '11B/G/N', '10/100'
                    ]):
                        return cleaned, res['method']
            
            # Priority 3: Look for hrDeviceDescr results (usually more specific than sysDescr)
            for res in all_results:
                if '1.3.6.1.2.1.25.3.2.1.3.1' in res['oid']:
                    cleaned = res['raw']
                    # Skip if it's just a generic description
                    if any(generic in cleaned.upper() for generic in [
                        'PRINT SERVER', 'ETHERNET', 'BUILT-IN', '11B/G/N', '10/100'
                    ]):
                        continue
                    
                    # Clean up the result
                    cleaned = re.sub(r'^.*?EPSON', 'EPSON', cleaned, flags=re.IGNORECASE)
                    cleaned = re.sub(r'^.*?Canon', 'Canon', cleaned, flags=re.IGNORECASE)
                    cleaned = re.sub(r'^.*?HP', 'HP', cleaned, flags=re.IGNORECASE)
                    cleaned = re.sub(r'^.*?Brother', 'Brother', cleaned, flags=re.IGNORECASE)
                    
                    # Apply Epson mapping
                    mapped_result = map_epson_model(cleaned)
                    return mapped_result, res['method'] + (" (mapped)" if mapped_result != cleaned else "")
            
            # Priority 4: Try to map any non-generic result we got
            for res in all_results:
                cleaned = res['raw']
                # Skip generic descriptions
                if any(generic in cleaned.upper() for generic in [
                    'PRINT SERVER', 'ETHERNET', 'BUILT-IN', '11B/G/N', '10/100'
                ]):
                    continue
                    
                mapped_result = map_epson_model(cleaned)
                if mapped_result != cleaned:  # Mapping was successful
                    return mapped_result, res['method'] + " (mapped)"
            
            # Priority 5: Return the best non-generic result with basic cleanup
            for res in all_results:
                cleaned = res['raw']
                # Skip obvious generic descriptions
                if any(generic in cleaned.upper() for generic in [
                    'PRINT SERVER', 'ETHERNET', 'BUILT-IN', '11B/G/N', '10/100'
                ]):
                    continue
                    
                cleaned = re.sub(r'^.*?EPSON', 'EPSON', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'^.*?Canon', 'Canon', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'^.*?HP', 'HP', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'^.*?Brother', 'Brother', cleaned, flags=re.IGNORECASE)
                return cleaned, res['method']
            
            # Last resort: return first result even if generic
            if all_results:
                first_result = all_results[0]
                cleaned = first_result['raw']
                return cleaned, first_result['method']
                    
        return None, None
    except Exception as e:
        return None, None

def get_oid_priority(oid, result):
    """Calculate priority score for OID results"""
    priority = 0
    
    # Epson-specific OIDs get highest priority
    if '1.3.6.1.4.1.1248' in oid:
        priority += 100
    
    # hrDeviceDescr gets medium-high priority
    if '1.3.6.1.2.1.25.3.2.1.3.1' in oid:
        priority += 80
    
    # sysDescr gets lower priority (can be generic)
    if '1.3.6.1.2.1.1.1.0' in oid:
        priority += 60
    
    # Boost priority if result contains actual model names
    if any(model in result.upper() for model in [
        'TM-U220IIB', 'TM-U220', 'TM-T82X', 'TM-T88', 'TM-T20', 'TM-T70', 'TM-T82',
        'UB-E04', 'UB-E03'
    ]):
        priority += 50
    
    # Reduce priority for generic descriptions
    if any(generic in result.upper() for generic in [
        'PRINT SERVER', 'ETHERNET', 'BUILT-IN', '11B/G/N', '10/100'
    ]):
        priority -= 30
    
    return priority

def is_valid_ip(ip):
    """Validate IP address format"""
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

def comprehensive_connectivity_test(ip):
    """Comprehensive connectivity test with detailed results"""
    results = {
        "ping": ping_host(ip),
        "snmp_port": test_snmp_port(ip),
        "reachable": False,
        "is_private": is_private_ip(ip)
    }
    
    results["reachable"] = results["ping"] or results["snmp_port"]
    return results

@app.route("/")
def home():
    """Welcome page with instructions"""
    return """
    <h1>🖨️ Network Printer Model Detector</h1>
    <h2>📖 Cara Pakai:</h2>
    <p><strong>GET</strong> <code>/get-printer?ip=IP_ADDRESS</code></p>
    
    <h3>✅ Contoh:</h3>
    <ul>
        <li><a href="/get-printer?ip=192.168.1.100">/get-printer?ip=192.168.1.100</a> (Standard)</li>
        <li><a href="/get-printer-fast?ip=192.168.68.89">/get-printer-fast?ip=192.168.68.89</a> (⚡ Fast Mode)</li>
    </ul>
    
    <h3>🔧 Test Form:</h3>
    <form action="/get-printer" method="get">
        <label>IP Address: </label>
        <input type="text" name="ip" placeholder="192.168.68.89" value="192.168.68.89">
        <button type="submit">🔍 Detect Model</button>
    </form>
    
    <h3>🛠️ Diagnostic Tools:</h3>
    <ul>
        <li><a href="/diagnose?ip=192.168.68.89">🔍 Diagnose Connection</a></li>
        <li><a href="/test-mapping">🔄 Test Model Mapping</a></li>
        <li><a href="/health">❤️ Health Check</a></li>
    </ul>
    
    <hr>
    <small>Server running | Created with ❤️ | Using pysnmp-lextudio (Python 3.12+ compatible)</small>
    """

@app.route("/diagnose")
def diagnose():
    """Diagnostic endpoint for troubleshooting"""
    ip = request.args.get("ip")
    
    if not ip:
        return jsonify({
            "error": "IP address not provided",
            "usage": "GET /diagnose?ip=192.168.1.100"
        }), 400

    if not is_valid_ip(ip):
        return jsonify({
            "error": "Invalid IP address format",
            "ip": ip
        }), 400

    # Run comprehensive tests
    connectivity = comprehensive_connectivity_test(ip)
    
    diagnosis = {
        "ip": ip,
        "connectivity_test": connectivity,
        "recommendations": []
    }
    
    # Check if this is a private IP being accessed from internet server
    if connectivity.get("is_private", False) and not connectivity["ping"]:
        diagnosis["recommendations"].append("🌐 This is a private IP address (local network)")
        diagnosis["recommendations"].append("🚫 Internet servers cannot reach private network IPs")
        diagnosis["recommendations"].append("ℹ️ This is normal behavior - not an error")
        diagnosis["recommendations"].append("🏠 For testing: Run this app locally in your network")
        diagnosis["recommendations"].append("🌍 For live server: Use a printer with public IP")
    elif not connectivity["ping"]:
        diagnosis["recommendations"].append("❌ Basic ping failed - device might be offline or unreachable")
    else:
        diagnosis["recommendations"].append("✅ Basic ping successful - device is online")
    
    if not connectivity["snmp_port"]:
        diagnosis["recommendations"].append("❌ SNMP port 161 not accessible - SNMP might be disabled")
        diagnosis["recommendations"].append("💡 Try enabling SNMP in printer settings")
        diagnosis["recommendations"].append("💡 Check if printer supports SNMP v1/v2c")
    else:
        diagnosis["recommendations"].append("✅ SNMP port 161 is accessible")
    
    # Try SNMP anyway even if port test fails
    model, method = get_printer_model(ip)
    if model:
        diagnosis["snmp_result"] = {
            "success": True,
            "model": model,
            "method": method
        }
        diagnosis["recommendations"].append("✅ SNMP query successful")
        
        # Check if mapping was applied
        if "(mapped)" in method:
            diagnosis["recommendations"].append("🔄 Internal device code was mapped to user-friendly name")
        
    else:
        diagnosis["snmp_result"] = {
            "success": False,
            "message": "No SNMP response received"
        }
        diagnosis["recommendations"].append("❌ SNMP query failed")
        diagnosis["recommendations"].append("💡 Try accessing printer web interface and enable SNMP")
        diagnosis["recommendations"].append("💡 Some printers use community string other than 'public'")
        diagnosis["recommendations"].append("💡 For Epson printers, check if SNMP is enabled in network settings")
    
    return jsonify(diagnosis)

@app.route("/get-printer-fast")
def get_printer_fast():
    """Fast endpoint - skip connectivity test completely"""
    ip = request.args.get("ip")
    
    if not ip:
        return jsonify({
            "error": "IP address not provided",
            "usage": "GET /get-printer-fast?ip=192.168.1.100"
        }), 400

    # Validate IP format
    if not is_valid_ip(ip):
        return jsonify({
            "error": "Invalid IP address format",
            "ip": ip
        }), 400

    # Get printer model directly - no connectivity test
    model, method = get_printer_model(ip)
    
    if model:
        return jsonify({
            "success": True,
            "ip": ip,
            "model": model,
            "detection_method": method,
            "message": "Printer model detected successfully (fast mode)"
        })
    else:
        return jsonify({
            "error": "Could not detect printer model",
            "ip": ip,
            "mode": "fast",
            "suggestions": [
                "Printer might not support SNMP",
                "SNMP might be disabled in printer settings",
                "Community string might not be 'public'",
                "Try regular mode: /get-printer?ip=" + ip
            ]
        }), 500

@app.route("/get-printer")
def get_printer():
    """Main endpoint to get printer model - improved version"""
    ip = request.args.get("ip")
    force = request.args.get("force") == "true"  # Skip connectivity test if force=true
    
    if not ip:
        return jsonify({
            "error": "IP address not provided",
            "usage": "GET /get-printer?ip=192.168.1.100",
            "tip": "Add &force=true to skip connectivity test"
        }), 400

    # Validate IP format
    if not is_valid_ip(ip):
        return jsonify({
            "error": "Invalid IP address format",
            "ip": ip
        }), 400

    # Test connectivity (unless forced to skip)
    if not force:
        connectivity = comprehensive_connectivity_test(ip)
        
        if not connectivity["reachable"]:
            # Provide different suggestions based on IP type
            if connectivity.get("is_private", False):
                suggestions = [
                    "🌐 This is a private IP (192.168.x.x, 10.x.x.x, 172.16-31.x.x)",
                    "🚫 Live server cannot reach private network IPs - this is normal",
                    "✅ For testing: Use force mode: add &force=true",
                    "🏠 For local testing: Run the app locally in your network",
                    "🌍 For live server: Use a printer with public IP address",
                    "🔍 Check diagnostic: /diagnose?ip=" + ip
                ]
                error_msg = "Private IP not reachable from internet server"
            else:
                suggestions = [
                    "Try with force mode: add &force=true to skip connectivity test",
                    "Check diagnostic: /diagnose?ip=" + ip,
                    "Make sure printer is powered on",
                    "Verify printer is accessible from internet"
                ]
                error_msg = "Cannot reach printer at this IP"
                
            return jsonify({
                "error": error_msg,
                "ip": ip,
                "connectivity_details": connectivity,
                "suggestions": suggestions
            }), 500

    # Get printer model (always try, even if connectivity test failed when forced)
    model, method = get_printer_model(ip)
    
    if model:
        return jsonify({
            "success": True,
            "ip": ip,
            "model": model,
            "detection_method": method,
            "message": "Printer model detected successfully"
        })
    else:
        return jsonify({
            "error": "Could not detect printer model",
            "ip": ip,
            "suggestions": [
                "Printer might not support SNMP",
                "SNMP might be disabled in printer settings",
                "Community string might not be 'public'",
                "Check diagnostic: /diagnose?ip=" + ip,
                "Try accessing printer web interface to enable SNMP"
            ]
        }), 500

@app.route("/test-mapping")
def test_mapping():
    """Test endpoint to demonstrate model code mapping"""
    test_cases = [
        "UB-E04",
        "UB-E03", 
        "EPSON UB-E04",
        "TM-T82X",
        "Unknown Model",
        "Canon LBP-2900"
    ]
    
    results = []
    for code in test_cases:
        mapped = map_epson_model(code)
        results.append({
            "original": code,
            "mapped": mapped,
            "mapping_applied": mapped != code
        })
    
    return jsonify({
        "service": "Model Code Mapping Test",
        "description": "Demonstrates how internal device codes are mapped to user-friendly names",
        "test_results": results,
        "example": {
            "before": "UB-E04",
            "after": "EPSON TM-U220IIB",
            "explanation": "Internal Epson code UB-E04 is automatically mapped to TM-U220IIB"
        }
    })

@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Network Printer Model Detector",
        "version": "2.6.0",
        "snmp_library": "pysnmp-lextudio (Python 3.12+ compatible fork)",
        "features": [
            "Enhanced Epson-specific OID detection",
            "Priority-based SNMP query processing",
            "Generic 'Print Server' response filtering",
            "Multi-community SNMP support",
            "Comprehensive connectivity testing", 
            "Diagnostic tools",
            "Force mode for strict networks",
            "Enhanced Epson model code mapping",
            "TM-T82X and TM-U220IIB specific detection",
            "Smart result selection algorithm",
            "Fast mode endpoint (⚡ /get-printer-fast)",
            "Python 3.12+ compatibility with pysnmp-lextudio"
        ]
    })

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    print("🖨️  Network Printer Model Detector v2.6 - Python 3.12+ Compatible")
    print("=" * 70)
    print(f"🌐 Server running on port: {port}")
    print("📖 Access your application via the Render URL")
    print("⚡ Fast API: /get-printer-fast?ip=192.168.68.89")
    print("🔍 Standard API: /get-printer?ip=192.168.68.89")
    print("🛠️ Diagnostic: /diagnose?ip=192.168.68.89")
    print("🔄 Enhanced Epson OIDs: TM-T82X, TM-U220IIB detection")
    print("⚡ Priority-based detection: Epson-specific OIDs first")
    print("🚫 Filters generic 'Print Server' responses")
    print("🐍 Using pysnmp-lextudio (maintained fork for Python 3.12+)")
    print("=" * 70)
    app.run(host="0.0.0.0", port=port, debug=False)
else:
    # Production mode: print startup info when imported by gunicorn
    print("🖨️  Network Printer Model Detector v2.6 - Python 3.12+ Compatible")
    print("=" * 70)
    print("🌐 Production mode with gunicorn WSGI server")
    print("📖 Access your application via the Render URL")
    print("⚡ Fast API: /get-printer-fast?ip=192.168.68.89")
    print("🔍 Standard API: /get-printer?ip=192.168.68.89")
    print("🛠️ Diagnostic: /diagnose?ip=192.168.68.89")
    print("🔄 Enhanced Epson OIDs: TM-T82X, TM-U220IIB detection")
    print("⚡ Priority-based detection: Epson-specific OIDs first")
    print("🚫 Filters generic 'Print Server' responses")
    print("🐍 Using pysnmp-lextudio (maintained fork for Python 3.12+)")
    print("=" * 70) 