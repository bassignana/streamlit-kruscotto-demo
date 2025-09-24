import sys
import requests

def reset_password(email, new_password, supabase_url, service_role_key):
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json"
    }

    # Step 1: Get user by email
    user_resp = requests.get(
        f"{supabase_url}/auth/v1/admin/users?email={email}",
        headers=headers
    )

    if user_resp.status_code != 200:
        print(f"ERROR: Failed to fetch user: {user_resp.status_code} {user_resp.text}")
        sys.exit(1)

    print("User response JSON:", user_resp.json())

    users = user_resp.json().get("users", [])
    if not users:
        print("ERROR: No user found with that email")
        sys.exit(1)

    if len(users) > 1:
        print("WARNING: Multiple users found with that email, using the first one")

    user_id = users[0]["id"]
    print("User id:", user_id)

    # Step 2: Update password
    data = {"password": new_password}
    update_resp = requests.put(
        f"{supabase_url}/auth/v1/admin/users/{user_id}",
        json=data,
        headers=headers
    )

    if update_resp.status_code == 200:
        print("SUCCESS: Password reset")
        print("Update response JSON:", update_resp.json())
    else:
        print(f"ERROR: Failed to update password: {update_resp.status_code} {update_resp.text}")
        sys.exit(1)

    # Suggest manual login test
    print("\nTry logging in manually with curl to verify:\n")
    print(f"""curl -X POST '{supabase_url}/auth/v1/token?grant_type=password' \\
  -H "Content-Type: application/json" \\
  -H "apikey: {service_role_key}" \\
  -d '{{"email":"{email}", "password":"{new_password}"}}'
""")


# Entry point
if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python reset_password_secure.py <email> <new_password> <supabase_url> <service_role_key>")
        sys.exit(1)

    email = sys.argv[1]
    new_password = sys.argv[2]
    supabase_url = sys.argv[3]
    service_role_key = sys.argv[4]

    reset_password(email, new_password, supabase_url, service_role_key)