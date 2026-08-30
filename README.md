# 💊 Smart Medicine Access System

A web application that helps users quickly find required medicines from nearby registered pharmacies, using real-time inventory data, GPS-based distance sorting, and prescription OCR scanning.

## 🩺 Problem Statement
Patients often struggle to find a required medicine quickly, especially when it is unavailable at nearby pharmacies. Calling or visiting multiple pharmacies wastes time, particularly during urgent situations.

## 💡 Solution
MedFinder connects users with nearby registered pharmacies in real time. Users can search for a medicine by name or upload a prescription image, and instantly see which nearby pharmacies have it in stock — sorted by distance, with directions and contact info.

## ✨ Features
- **User & Pharmacy Authentication** — separate secure registration/login for patients and pharmacies (hashed passwords)
- **Medicine Search** — search by name, see live stock availability across all registered pharmacies
- **GPS-Based Distance Sorting** — results sorted by real distance (Haversine formula) from the user's current location
- **Get Directions** — one-click Google Maps directions to the pharmacy
- **Prescription OCR** — upload a prescription photo; Tesseract OCR extracts text and auto-matches known medicines
- **Medicine Availability Requests** — users can request a medicine that's out of stock; pharmacies see and fulfill these requests
- **Pharmacy Dashboard** — pharmacies manage their own inventory (add/update stock, price, quantity)
- **Admin Dashboard** — system-wide overview (users, pharmacies, medicines, requests) with management controls (delete users/pharmacies)
- **Auto Geocoding** — pharmacies find their exact coordinates automatically from a typed address (via OpenStreetMap Nominatim)

## 🛠️ Tech Stack
- **Backend:** Python, Flask
- **Database:** SQLite
- **Frontend:** HTML, CSS (custom, no framework), vanilla JavaScript
- **OCR:** Tesseract OCR (pytesseract)
- **Geolocation:** Browser Geolocation API + OpenStreetMap Nominatim (geocoding)
- **Maps:** Google Maps (directions link)

## 📂 Project Structure