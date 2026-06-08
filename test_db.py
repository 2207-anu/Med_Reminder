from db_postgres import init_db, register_user, login_user

init_db()
print("✅ Tables created!")

res = register_user("Test User", "test@example.com", "Test@123")
print("Register:", res)

res = login_user("test@example.com", "Test@123")
print("Login:", res)

res = login_user("admin@medremind.com", "Admin@123")
print("Admin login:", res)