from identidad.models import UsuarioMICI

email = 'director@mici.gob.pa'
if not UsuarioMICI.objects.filter(email=email).exists():
    print(f"Creating user {email}...")
    user = UsuarioMICI.objects.create_user(
        username='director',
        email=email,
        password='password123',
        first_name='Sr.',
        last_name='Director',
        rol=UsuarioMICI.DIRECTOR,
        cedula='8-300-300'
    )
    user.save()
    print("User created.")
else:
    print(f"User {email} already exists.")
    user = UsuarioMICI.objects.get(email=email)
    # Ensure role is correct
    if user.rol != UsuarioMICI.DIRECTOR:
        user.rol = UsuarioMICI.DIRECTOR
        user.save()
        print("Updated role to DIRECTOR.")

print(f"Director: {user.get_full_name()} ({user.rol})")
