# generate_keys.py
import ecdsa

# Generate a new private key using NIST256p
sk = ecdsa.SigningKey.generate(curve=ecdsa.NIST256p)
vk = sk.verifying_key

# Save the keys
with open("ecdsa_private.pem", "wb") as f:
    f.write(sk.to_pem())

with open("ecdsa_public.pem", "wb") as f:
    f.write(vk.to_pem())

print("Keys generated successfully.")

