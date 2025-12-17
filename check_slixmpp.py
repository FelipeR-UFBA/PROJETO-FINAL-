import slixmpp
import inspect

print(f"Slixmpp Version: {slixmpp.__version__}")
try:
    sig = inspect.signature(slixmpp.ClientXMPP.connect)
    print(f"Connect Signature: {sig}")
except Exception as e:
    print(f"Error inspecting: {e}")
