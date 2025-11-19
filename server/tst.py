import bcrypt
print(bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode())
