from werkzeug.security import generate_password_hash

def generar_hash(password):
    hash_generado = generate_password_hash(password)
    print("Hash generado:")
    print(hash_generado)
    return hash_generado

# Ejemplo de uso
if __name__ == "__main__":
    contraseña = input("Ingresa la contraseña: ")
    generar_hash(contraseña)
