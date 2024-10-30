import bcrypt
import sys
from getpass import getpass

def generate_hash(password):
    password_bytes = password.encode('utf-8')
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode()

if __name__ == "__main__":
    # 如果命令行提供了参数，使用参数作为密码
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        # 使用 getpass 隐藏密码输入
        password = getpass("Enter password to hash: ")
    
    hashed_password = generate_hash(password)
    print("Hash:", hashed_password, "\n")
