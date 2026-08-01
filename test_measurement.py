import requests

lat = 17.443464
lon = 78.47489

url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}"

response = requests.get(
    url,
    headers={
        "User-Agent": "India-Air-Quality-Analysis (your_email@gmail.com)"
    }
)

print(response.status_code)
print(response.json())