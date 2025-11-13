// ESP32 Firmware: Wi-Fi & Basic HTTP POST
// This code runs on the ESP32 microcontroller.

#include <WiFi.h>
#include <HTTPClient.h> // For making HTTP requests
#include <ArduinoJson.h> // For creating JSON payloads (install via Library Manager)

// --- WiFi Credentials ---
// REPLACE WITH YOUR ACTUAL WIFI NETWORK NAME AND PASSWORD
const char* ssid = "Airtel_abhi_7223";
const char* password = "Air@30889";

// --- Flask App Configuration ---
// REPLACE WITH THE ACTUAL LOCAL IP ADDRESS OF THE COMPUTER RUNNING YOUR FLASK APP
// E.g., "192.168.1.100" or "10.0.0.5"
const char* flaskAppHost = "192.168.1.8"; 
const int flaskAppPort = 5000; // Default Flask port
const char* statusUpdateEndpoint = "/api/clamp_status_update"; // Your Flask API endpoint

// --- Clamp Details (Simulated for now, will be dynamic with sensors later) ---
// REPLACE WITH A UNIQUE CLAMP ID FOR YOUR PHYSICAL DEVICE
String clampId = "PHYSICAL_CLAMP_001";
String clampCity = "Pune";
int batteryLevel = 95; // Simulated initial battery level
String clampStatus = "available"; // Simulated initial status

// Function to connect to Wi-Fi
void connectToWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");
  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());
}

// Function to send status update to Flask backend
void sendStatusUpdate() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    String serverPath = "http://" + String(flaskAppHost) + ":" + String(flaskAppPort) + String(statusUpdateEndpoint);
    
    Serial.print("Sending status to: ");
    Serial.println(serverPath);

    http.begin(serverPath); // Specify request destination
    http.addHeader("Content-Type", "application/json"); // Specify content-type header

    // Create JSON payload
    StaticJsonDocument<200> doc; // Adjust size as needed
    doc["clamp_id"] = clampId;
    doc["status"] = clampStatus;
    doc["city"] = clampCity;
    doc["battery_level"] = batteryLevel;

    String requestBody;
    serializeJson(doc, requestBody);

    Serial.print("Request Body: ");
    Serial.println(requestBody);

    int httpResponseCode = http.POST(requestBody); // Send the HTTP POST request

    if (httpResponseCode > 0) {
      Serial.printf("HTTP Response code: %d\n", httpResponseCode);
      String payload = http.getString();
      Serial.println(payload);
    } else {
      Serial.printf("HTTP Error: %s\n", http.errorToString(httpResponseCode).c_str());
    }
    http.end(); // Free resources
  } else {
    Serial.println("WiFi not connected. Cannot send status update.");
  }
}

void setup() {
  Serial.begin(115200); // Initialize serial communication for debugging
  connectToWiFi(); // Connect to Wi-Fi network
  delay(2000); // Give some time for connection to stabilize
}

void loop() {
  // Simulate battery drain for realism (optional)
  if (batteryLevel > 0) {
    batteryLevel -= 1; // Drain 1% per loop cycle
  } else {
    batteryLevel = 0;
    clampStatus = "low_battery"; // Change status if battery is zero
  }

  // Send status update every 5 seconds
  sendStatusUpdate();
  delay(5000); // Wait for 5 seconds before sending next update
}

