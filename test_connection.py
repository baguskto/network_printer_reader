#!/usr/bin/env python3
"""
Test script untuk memverifikasi koneksi SNMP dan dependencies
"""

import sys
import socket

def test_imports():
    """Test if all required libraries are installed"""
    print("🔧 Testing imports...")
    try:
        import flask
        print("✅ Flask installed")
    except ImportError:
        print("❌ Flask not installed - run: pip install flask")
        return False
    
    try:
        from pysnmp.hlapi import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
        print("✅ PySNMP installed")
    except ImportError:
        print("❌ PySNMP not installed - run: pip install pysnmp")
        return False
    
    return True

def test_snmp_connection(ip):
    """Test SNMP connection to a given IP"""
    print(f"\n🔍 Testing SNMP connection to {ip}...")
    
    # Test port connectivity
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((ip, 161))
        sock.close()
        if result == 0:
            print(f"✅ Port 161 (SNMP) is reachable on {ip}")
        else:
            print(f"❌ Cannot reach port 161 on {ip}")
            return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False
    
    # Test SNMP query
    try:
        from pysnmp.hlapi import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
        
        iterator = getCmd(
            SnmpEngine(),
            CommunityData('public', mpModel=0),
            UdpTransportTarget((ip, 161), timeout=3, retries=1),
            ContextData(),
            ObjectType(ObjectIdentity('1.3.6.1.2.1.1.1.0'))  # sysDescr
        )

        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
        
        if errorIndication:
            print(f"❌ SNMP Error: {errorIndication}")
            return False
        elif errorStatus:
            print(f"❌ SNMP Error: {errorStatus.prettyPrint()} at {errorIndex and varBinds[int(errorIndex) - 1] or '?'}")
            return False
        else:
            result = str(varBinds[0][1])
            print(f"✅ SNMP Response: {result}")
            return True
            
    except Exception as e:
        print(f"❌ SNMP test failed: {e}")
        return False

def main():
    print("🖨️ Network Printer Model Detector - Connection Test")
    print("=" * 55)
    
    # Test imports
    if not test_imports():
        print("\n❌ Please install missing dependencies first!")
        sys.exit(1)
    
    print("\n" + "=" * 55)
    ip = input("🌐 Enter printer IP to test (or press Enter to skip): ").strip()
    
    if ip:
        if test_snmp_connection(ip):
            print(f"\n✅ Great! Printer at {ip} is responding to SNMP queries")
            print("🚀 You can now run the main application: python printer_model_api.py")
        else:
            print(f"\n❌ Cannot communicate with printer at {ip}")
            print("💡 Tips:")
            print("   - Make sure printer is powered on")
            print("   - Check if printer is in the same network")
            print("   - Verify the IP address is correct")
            print("   - Some printers may have SNMP disabled")
    else:
        print("\n✅ Dependencies check passed!")
        print("🚀 You can now run: python printer_model_api.py")
    
    print("\n" + "=" * 55)

if __name__ == "__main__":
    main() 