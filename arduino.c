#include <WiFiS3.h>
#include <FastLED.h>
#include <EEPROM.h>
#include <WiFiClient.h>
#include <ArduinoHttpClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "DunkAnimation.h"
#include <vector>
#define EEPROM_SIZE 128
#define CLIENT_ID_LENGTH 40
#define CLIENT_ID_ADDR 96
#define LED_PIN 6
#define WIDTH 48
#define HEIGHT 32
#define NUM_LEDS (WIDTH * HEIGHT)
#define BRIGHTNESS 80


Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);
CRGB leds[NUM_LEDS];
LiquidCrystal_I2C lcd(0x27, 20, 4);
const int AP_PORT = 80;
WiFiServer apServer(AP_PORT);
std::vector<String> displayedSubs;

// const char* ssid = "Kyoto";
// const char* password = "T0d3d0j0_18!!";
const char* ssid = "";
const char* password = "";


const char* serverAddress = "lyvframe.com";
const int port = 5000;


WiFiClient client;


const char* AP_SSID = "NBA-Lights";
const char* AP_PASS = "nbatracker123";
int lastShotIndex = -1;
String lastGameId = "";
String clientId = "be3c14f8-c257-48f0-becd-0fa0c367f6aa";
// String client_id="be3c14f8-c257-48f0-becd-0fa0c367f6aa";
String client_id = "";
int lastKnownPeriod = 0;
bool gameOverAnnounced = false;
struct WiFiCredentials {
  char ssid[32];
  char pass[64];
};


String current_sport = "nba";
int sportCheckIntervalMs = 10000;  // Check every 10 seconds
unsigned long lastSportCheckTime = 0;


String buildPath(const String& endpoint, const String& query) {
  return "/" + current_sport + "/" + endpoint + "?" + query;
}




String homeAbbrev = "?";
String awayAbbrev = "?";
String lastShotTime = "0";
String nextShotTime = "0";
// WiFiSSLClient wifi;
// HttpClient httpClient = HttpClient(wifi, "lyvframe.com", 443);


WiFiClient wifiClient;
HttpClient httpClient = HttpClient(wifiClient, "lyvframe.com", 5000);


// 1) updateCurrentSport — create + tear down its own client
void updateCurrentSport(const String& clientId) {
  unsigned long now = millis();
  if (now - lastSportCheckTime < sportCheckIntervalMs) return;
  lastSportCheckTime = now;

  // build URL
  String path = "/nba/current_sport?client_id=" + clientId;

  // create local HttpClient
  HttpClient http(wifiClient, serverAddress, port);
  http.get(path);

  int statusCode = http.responseStatusCode();
  if (statusCode == 200) {
    String body = http.responseBody();
    StaticJsonDocument<128> doc;
    if (deserializeJson(doc, body) == DeserializationError::Ok
        && doc.containsKey("sport")) {
      current_sport = String(doc["sport"]);
      Serial.print("[Sport] Updated to: ");
      Serial.println(current_sport);
    }
  } else {
    Serial.print("[Sport] Failed, status: ");
    Serial.println(statusCode);
  }

  http.stop();  // <— ensure the socket is closed
}


bool selectGame(const String& gameId) {
  String path = buildPath("select_game", "gameId=" + gameId + "&client_id=" + client_id);


  httpClient.get(path);
  int code = httpClient.responseStatusCode();
  String body = httpClient.responseBody();
  httpClient.stop();


  if (code == 200) {
    StaticJsonDocument<256> doc;
    if (deserializeJson(doc, body) == DeserializationError::Ok) {
      String newSport = doc["sport"] | "nba";
      current_sport = newSport;
      Serial.print("🔀 Switched to sport: ");
      Serial.println(current_sport);
    }
    Serial.println("✅ Game selected successfully");
    lastShotIndex = -1;
    lastGameId = gameId;
    lastKnownPeriod = 0;
    gameOverAnnounced = false;
    return true;
  } else {
    Serial.print("❌ Failed to select game, status: ");
    Serial.println(code);
    return false;
  }
}


bool selectSport(const String& sport) {
  String path = "/api/select_sport?client_id=" + client_id + "&sport=" + sport;
  httpClient.get(path);
  int code = httpClient.responseStatusCode();
  String body = httpClient.responseBody();
  httpClient.stop();


  if (code == 200) {
    Serial.print("✅ Sport selected: ");
    Serial.println(sport);
    current_sport = sport;  // Update local sport variable too
    return true;
  } else {
    Serial.print("❌ Failed to select sport, status: ");
    Serial.println(code);
    return false;
  }
}


void pausePolling() {
  String path = "/pause?client_id=" + client_id;
  httpClient.post(path);
}
void resumePolling() {
  String path = "/resume?client_id=" + client_id;
  httpClient.post(path);
}
String generateRandomClientID() {
  String id = "";
  for (int i = 0; i < 8; i++) {
    id += String(random(0, 16), HEX);
  }
  return id;
}
void saveClientID(const String& id) {
  for (int i = 0; i < CLIENT_ID_LENGTH; i++) {
    char c = (i < id.length()) ? id[i] : '\0';
    EEPROM.write(CLIENT_ID_ADDR + i, c);
  }
}


String loadClientID() {
  char idBuffer[CLIENT_ID_LENGTH + 1];
  for (int i = 0; i < CLIENT_ID_LENGTH; i++) {
    char c = EEPROM.read(CLIENT_ID_ADDR + i);
    if (c == 0xFF || c == 0 || c < 32 || c > 126) {
      idBuffer[i] = '\0';
      break;
    } else {
      idBuffer[i] = c;
    }
  }
  idBuffer[CLIENT_ID_LENGTH] = '\0';
  return String(idBuffer);
}
bool isValidClientID(const String& id) {
  if (id.length() == 0) return false;
  for (unsigned int i = 0; i < id.length(); i++) {
    char c = id[i];
    if (c < 32 || c > 126) return false;
  }
  return true;
}


void setup() {
  Serial.begin(115200);
  strip.show();
  delay(1000);
  FastLED.addLeds<NEOPIXEL, LED_PIN>(leds, NUM_LEDS);
  FastLED.setBrightness(BRIGHTNESS);
  FastLED.clear();
  lightBaskets();
  FastLED.show();
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("NBA Shot Tracker");
  lcd.setCursor(0, 1);
  lcd.print("Waiting for data...");


  client_id = "be3c14f8-c257-48f0-becd-0fa0c367f6aa";
  Serial.print("Using hardcoded client_id: ");
  Serial.println(client_id);
  if (!isValidClientID(client_id) || client_id == "00000000") {
    client_id = generateRandomClientID();
    saveClientID(client_id);
    Serial.print("Generated and saved new client_id: ");
    Serial.println(client_id);
  } else {
    Serial.print("Loaded existing client_id: ");
    Serial.println(client_id);
  }




  WiFiCredentials creds = loadCredentials();
  String ssid = String(creds.ssid);
  String pass = String(creds.pass);


  if (ssid.length() == 0 || pass.length() == 0 || ssid[0] == '\0') {
    if (!startCaptivePortal()) {
      Serial.println("\u274C Could not start captive portal; halting.");
      while (true) delay(1000);
    }
  } else {
    connectToWiFi(ssid.c_str(), pass.c_str());
    if (WiFi.status() != WL_CONNECTED || WiFi.localIP() == IPAddress(0, 0, 0, 0)) {
      if (!startCaptivePortal()) {
        Serial.println("\u274C Could not start captive portal; halting.");
        while (true) delay(1000);
      }
    } else {
      // WiFi connected successfully


      // <<< ADD THIS BLOCK: Select sport first >>>
      String desiredSport = "nfl";  // Change to "nba" if you want NBA
      if (selectSport(desiredSport)) {
        Serial.println("✅ Sport selected successfully.");
      } else {
        Serial.println("❌ Failed to select sport.");
      }


      Serial.println("WiFi connected, selecting game...");
      String testGameId = "401547518";  // NFL or NBA game ID depending on sport
      if (selectGame(testGameId)) {
        Serial.println("✅ Game selected successfully.");
      } else {
        Serial.println("❌ Failed to select game.");
      }
    }
  }
}


void saveCredentials(const WiFiCredentials& creds) {
  const uint8_t* p = (const uint8_t*)&creds;
  for (int i = 0; i < sizeof(WiFiCredentials); i++) {
    EEPROM.write(i, p[i]);
  }
}
WiFiCredentials loadCredentials() {
  WiFiCredentials creds;
  uint8_t* p = (uint8_t*)&creds;
  for (int i = 0; i < sizeof(WiFiCredentials); i++) {
    p[i] = EEPROM.read(i);
  }
  EEPROM.end();
  return creds;
}
const int middle_row = HEIGHT / 2;
const int left_basket_x1 = 1;
const int left_basket_x2 = 2;
const int right_basket_x1 = WIDTH - 3;
const int right_basket_x2 = WIDTH - 2;
// int XY(int x,int y){
//  if(x<0||x>=WIDTH||y<0||y>=HEIGHT)return -1;
//  const int PANEL_WIDTH=16;
//  const int PANEL_HEIGHT=16;
//  int panel_col=x/PANEL_WIDTH;
//  int panel_row=y/PANEL_HEIGHT;
//  int panel_index;
//  if(panel_row==1){
//   panel_index=5-panel_col;
//  }else{
//   panel_index=panel_col;
//  }
//  int local_x=x%PANEL_WIDTH;
//  int local_y=y%PANEL_HEIGHT;
//  bool left_to_right=(local_y%2==0);
//  int index_in_panel=left_to_right?local_y*PANEL_WIDTH+local_x:local_y*PANEL_WIDTH+(PANEL_WIDTH-1-local_x);
//  return panel_index*(PANEL_WIDTH*PANEL_HEIGHT)+index_in_panel;
// }
void lightBaskets() {
  leds[XY(1, 15)] = CRGB::White;
  leds[XY(1, 16)] = CRGB::White;
  leds[XY(2, 15)] = CRGB::White;
  leds[XY(2, 16)] = CRGB::White;
  leds[XY(45, 15)] = CRGB::White;
  leds[XY(45, 16)] = CRGB::White;
  leds[XY(46, 15)] = CRGB::White;
  leds[XY(46, 16)] = CRGB::White;
  FastLED.show();
}
void flashBorderGreen() {
  for (int x = 0; x < WIDTH; x++) {
    leds[XY(x, 0)] = CRGB::Green;
    leds[XY(x, HEIGHT - 1)] = CRGB::Green;
  }
  for (int y = 1; y < HEIGHT - 1; y++) {
    leds[XY(0, y)] = CRGB::Green;
    leds[XY(WIDTH - 1, y)] = CRGB::Green;
  }
  FastLED.show();
  delay(800);
  for (int x = 0; x < WIDTH; x++) {
    leds[XY(x, 0)] = CRGB::Black;
    leds[XY(x, HEIGHT - 1)] = CRGB::Black;
  }
  for (int y = 1; y < HEIGHT - 1; y++) {
    leds[XY(0, y)] = CRGB::Black;
    leds[XY(WIDTH - 1, y)] = CRGB::Black;
  }
  FastLED.show();
}
void flashShot(int x, int y, const char* result) {
  if (x < 0 || y < 0) {
    Serial.println("🎯 Skipping shot with invalid coordinates.");
    return;
  }
  int ledIndex = XY(x, y);
  if (ledIndex < 0 || ledIndex >= NUM_LEDS) return;
  String resultStr = String(result);
  resultStr.toLowerCase();
  bool madeShot = (resultStr.indexOf("made") >= 0);
  leds[ledIndex] = madeShot ? CRGB::Green : CRGB::Red;
  FastLED.show();
  delay(1000);
  leds[ledIndex] = CRGB::Black;
  FastLED.show();
  if (madeShot) {
    flashBorderGreen();
  }
  lightBaskets();
  FastLED.show();
}
String urlDecode(const String& input) {
  String decoded = "";
  char temp[] = "0x00";
  unsigned int len = input.length();
  for (unsigned int i = 0; i < len; i++) {
    char c = input.charAt(i);
    if (c == '+') decoded += ' ';
    else if (c == '%' && i + 2 < len) {
      temp[2] = input.charAt(i + 1);
      temp[3] = input.charAt(i + 2);
      decoded += (char)strtol(temp, NULL, 16);
      i += 2;
    } else {
      decoded += c;
    }
  }
  return decoded;
}


bool startCaptivePortal() {
  Serial.println("\xF0\x9F\x94\xA7 Starting captive portal...");
  WiFi.end();


  if (!WiFi.beginAP(AP_SSID, AP_PASS)) {
    Serial.println("\u274C Failed to start Access Point.");
    return false;
  }


  Serial.print("AP IP address: ");
  Serial.println(WiFi.softAPIP());
  apServer.begin();


  unsigned long startTime = millis();


  while (millis() - startTime < 120000) {
    WiFiClient client = apServer.available();


    if (client) {
      Serial.println("\xF0\x9F\x93\xB6 Client connected to captive portal.");
      unsigned long clientStart = millis();
      while (!client.available() && (millis() - clientStart < 3000)) delay(10);


      String request = client.readStringUntil('\r');
      client.readStringUntil('\n');


      if (request.indexOf("GET / ") >= 0) {
        client.println("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body><h2>Enter WiFi Credentials</h2>");
        client.println("<form action='/connect' method='get'>SSID: <input name='ssid'><br>Password: <input name='pass' type='password'><br><input type='submit'></form></body></html>");


      } else if (request.indexOf("GET /connect?ssid=") >= 0) {
        int ssidIndex = request.indexOf("ssid=");
        int passIndex = request.indexOf("pass=");
        String ssid = urlDecode(request.substring(ssidIndex + 5, request.indexOf('&', ssidIndex)));
        String pass = urlDecode(request.substring(passIndex + 5, request.indexOf(' ', passIndex)));


        Serial.print("🌐 Trying to connect to SSID: ");
        Serial.println(ssid);


        WiFi.end();  // Ensure clean state
        WiFi.begin(ssid.c_str(), pass.c_str());


        unsigned long connectStart = millis();
        while (WiFi.status() != WL_CONNECTED && millis() - connectStart < 10000) {
          delay(250);
          Serial.print(".");
        }


        if (WiFi.status() == WL_CONNECTED && WiFi.localIP() != INADDR_NONE) {
          Serial.println("\n✅ WiFi connection successful!");


          WiFiCredentials creds;
          ssid.toCharArray(creds.ssid, sizeof(creds.ssid));
          pass.toCharArray(creds.pass, sizeof(creds.pass));
          saveCredentials(creds);


          client.println("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body><h2>WiFi Connected! Restarting device...</h2></body></html>");
          delay(2000);
          NVIC_SystemReset();
          return true;
        } else {
          Serial.print("\n❌ Failed to connect. WiFi.status(): ");
          Serial.println(WiFi.status());
          Serial.print("Local IP: ");
          Serial.println(WiFi.localIP());
        }


      } else {
        client.println("HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n<html><body><h2>404 Not Found</h2></body></html>");
      }


      client.flush();
      client.stop();
    }


    delay(10);
  }


  Serial.println("\u23F3 Captive portal timed out.");
  return false;
}




void connectToWiFi(const char* ssid, const char* pass) {
  Serial.print("Connecting to WiFi SSID: ");
  Serial.println(ssid);
  WiFi.begin(ssid, pass);
  for (int i = 0; i < 30; i++) {
    IPAddress ip = WiFi.localIP();
    if (WiFi.status() == WL_CONNECTED && ip != IPAddress(0, 0, 0, 0)) {
      Serial.println("\n\u2705 Connected to WiFi!");
      Serial.print("IP Address: ");
      Serial.println(ip);
      return;
    }
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n\u274C Failed to connect or obtain IP address.");
}


String getCurrentGameId() {
  String path = buildPath("current_game", "client_id=" + client_id);
  httpClient.get(path);
  int code = httpClient.responseStatusCode();
  if (code != 200) {
    httpClient.stop();
    return "";
  }
  String body = httpClient.responseBody();
  httpClient.stop();


  StaticJsonDocument<128> doc;
  if (deserializeJson(doc, body) != DeserializationError::Ok) {
    return "";
  }
  return doc["game_id"].as<String>();
}


bool isPaused() {
  httpClient.get("/is_paused?client_id=" + client_id);
  int statusCode = httpClient.responseStatusCode();
  if (statusCode == 200) {
    String resp = httpClient.responseBody();
    httpClient.stop();  // <-- ADD THIS
    StaticJsonDocument<64> doc;
    if (deserializeJson(doc, resp) == DeserializationError::Ok) {
      return doc["paused"];
    }
  } else {
    httpClient.stop();  // <-- ADD THIS
  }
  return false;
}


unsigned long lastPollTime = 0;
const unsigned long pollIntervalMs = 500;
String replaceSpecialChars(const char* input) {
  String output = "";
  for (int i = 0; input[i] != '\0'; i++) {
    char c = input[i];
    if (c == 'ö' || c == 'Ö') output += 'o';
    else if (c == 'ä' || c == 'Ä') output += 'a';
    else if (c == 'ü' || c == 'Ü') output += 'u';
    else if (c == 'ß') output += "ss";
    else output += c;
  }
  return output;
}
String filterToAscii(const char* input) {
  String output = "";
  for (int i = 0; input[i] != '\0'; i++) {
    char c = input[i];
    if (c >= 32 && c <= 126) output += c;
    else output += ' ';
  }
  return output;
}
void updateScoreLCD(const char* teamHome, const char* scoreHome, const char* teamAway, const char* scoreAway, const char* desc, const char* clockRaw, int period) {
  lcd.clear();
  String cleanDesc = filterToAscii(replaceSpecialChars(desc).c_str());
  lcd.setCursor(0, 0);
  for (int i = 0; i < 20; i++) {
    lcd.print(i < cleanDesc.length() ? cleanDesc[i] : ' ');
  }
  lcd.setCursor(0, 1);
  for (int i = 20; i < 40; i++) {
    lcd.print(i < cleanDesc.length() ? cleanDesc[i] : ' ');
  }
  String clockStr = String(clockRaw);
  if (clockStr.startsWith("PT")) {
    clockStr.replace("PT", "");
    clockStr.replace("M", ":");
    clockStr.replace("S", "");
    if (clockStr.length() < 5) clockStr = "0" + clockStr;
  }
  String quarterTime = "Q" + String(period) + " " + clockStr;
  lcd.setCursor(0, 2);
  lcd.print(quarterTime.substring(0, 20));
  String scoreLine = String(teamHome) + " " + scoreHome + " - " + String(teamAway) + " " + scoreAway;
  lcd.setCursor(0, 3);
  lcd.print(scoreLine.substring(0, 20));
}


void threePointMadeAnimation(int shotX, int shotY) {
  const int maxRadius = 3;
  const float tolerance = 0.3;
  const int frameDelay = 200;  // milliseconds


  // 1. Prepare static background: clear, light baskets, draw border
  fill_solid(leds, NUM_LEDS, CRGB::Black);
  lightBaskets();
  // draw solid green border
  for (int x0 = 0; x0 < WIDTH; x0++) {
    leds[XY(x0, 0)] = CRGB::Green;
    leds[XY(x0, HEIGHT - 1)] = CRGB::Green;
  }
  for (int y0 = 1; y0 < HEIGHT - 1; y0++) {
    leds[XY(0, y0)] = CRGB::Green;
    leds[XY(WIDTH - 1, y0)] = CRGB::Green;
  }
  FastLED.show();


  // 2. Ripple outward, leaving border and baskets intact
  for (int radius = 0; radius <= maxRadius; radius++) {
    // compute this ring's pixels
    std::vector<int> ringPixels;
    for (int xi = 0; xi < WIDTH; xi++) {
      for (int yi = 0; yi < HEIGHT; yi++) {
        float dist = sqrtf((xi - shotX) * (xi - shotX) + (yi - shotY) * (yi - shotY));
        if (fabs(dist - radius) < tolerance) {
          int idx = XY(xi, yi);
          if (idx >= 0 && idx < NUM_LEDS) {
            ringPixels.push_back(idx);
            leds[idx] = CRGB::Green;
          }
        }
      }
    }


    FastLED.show();
    delay(frameDelay);


    // clear only this ring before next radius
    for (int idx : ringPixels) {
      leds[idx] = CRGB::Black;
    }
  }


  // 3. Clear the border as well
  for (int x0 = 0; x0 < WIDTH; x0++) {
    leds[XY(x0, 0)] = CRGB::Black;
    leds[XY(x0, HEIGHT - 1)] = CRGB::Black;
  }
  for (int y0 = 1; y0 < HEIGHT - 1; y0++) {
    leds[XY(0, y0)] = CRGB::Black;
    leds[XY(WIDTH - 1, y0)] = CRGB::Black;
  }


  // 4. Finally, relight only the baskets
  lightBaskets();
  FastLED.show();
}

void checkSubLog() {
  HttpClient http(client, serverAddress, port);

  String url = "http://" + String(serverAddress) + ":" + String(port) + "/nba/get_sub_log?client_id=" + clientId;
  http.get(url);

  int statusCode = http.responseStatusCode();
  if (statusCode == 200) {
    String response = http.responseBody();

    StaticJsonDocument<256> doc;
    DeserializationError err = deserializeJson(doc, response);

    if (!err && doc.containsKey("msg")) {
      String msg = doc["msg"];
      if (!subsContains(msg)) {
        Serial.println(msg);  // ➤ "SUB IN: B. Hield", etc.
        displayedSubs.push_back(msg);
        if (displayedSubs.size() > 50) {
          displayedSubs.erase(displayedSubs.begin());
        }
      }
    }
  } else {
    Serial.print("HTTP error: ");
    Serial.println(statusCode);
  }

  http.stop();
}

unsigned long lastSubCheck = 0;
const unsigned long subCheckInterval = 2000;

bool subsContains(const String& msg) {
  for (const auto& s : displayedSubs) {
    if (s == msg) return true;
  }
  return false;
}

void loop() {
  // Ensure Wi-Fi
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ WiFi disconnected, skipping polling.");
    delay(2000);
    return;
  }

  unsigned long now = millis();

  // Polling interval
  if (now - lastPollTime < pollIntervalMs) return;
  lastPollTime = now;

  fetchNextShot();
}



void popShot(int shotIndex) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("🚫 WiFi not connected, cannot pop shot.");
    return;
  }


  HttpClient client = HttpClient(wifiClient, serverAddress, port);
  String path = "/nba/pop_shot";


  String jsonBody = "{\"client_id\": \"" + client_id + "\", \"shot_index\": " + String(shotIndex) + "}";

  client.beginRequest();
  client.post(path);
  client.sendHeader("Content-Type", "application/json");
  client.sendHeader("Content-Length", jsonBody.length());
  client.beginBody();
  client.print(jsonBody);
  client.endRequest();


  int statusCode = client.responseStatusCode();
  String response = client.responseBody();
  client.stop();
}


void handleShot(const JsonDocument& doc) {
  // (0) reset detection
  if (doc["reset"] == true) {
    Serial.println("🔁 Reset detected — resetting lastShotIndex.");
    lastShotIndex = -1;
    return;
  }

  // (1) extract all needed fields
  int shotIndex = doc["index"];
  int rawPeriod = doc["period"] | 1;
  int period = max(rawPeriod, 1);
  const char* desc = doc["description"] | "";
  const char* clock = doc["clock"] | "";
  const char* statusText = doc["gameStatusText"] | "";

  const char* player = doc["player"] | "Unknown";
  const char* team = doc["team"] | "UNK";
  const char* result = doc["result"];

  const char* scoreHome = doc["scoreHome"] | "?";
  const char* scoreAway = doc["scoreAway"] | "?";
  int x = doc["x"];
  int y = doc["y"];

  // Team abbreviations
  String awayTeamStr = doc["away_team"] | "AWAY";
  String homeTeamStr = doc["home_team"] | "HOME";
  const char* awayTeam = awayTeamStr.c_str();
  const char* homeTeam = homeTeamStr.c_str();

  // (1b) Check for dunk and made shot robustly
  bool isDunk = false;
  bool madeShot = false;

  // Check subType for "DUNK"
  if (doc.containsKey("subType")) {
    String subType = String(doc["subType"] | "");
    subType.toUpperCase();
    if (subType == "DUNK") {
      isDunk = true;
    }
  } else {
    // fallback: check description text for "DUNK"
    String descStr = String(desc);
    descStr.toUpperCase();
    if (descStr.indexOf("DUNK") >= 0) {
      isDunk = true;
    }
  }

  // Check shotResult for "Made"
  if (doc.containsKey("shotResult")) {
    String shotResult = String(doc["shotResult"] | "");
    shotResult.toUpperCase();
    if (shotResult == "MADE") {
      madeShot = true;
    }
  } else {
    // fallback: check result field
    String resStr = String(result);
    resStr.toUpperCase();
    if (resStr.indexOf("MADE") >= 0) {
      madeShot = true;
    }
  }

  // (2) skip duplicates
  Serial.print("Received shot index: ");
  Serial.println(shotIndex);
  if (shotIndex <= lastShotIndex) {
    Serial.println("⏭️ Skipping — not newer than last processed.");
    return;
  }
  lastShotIndex = shotIndex;


  // (3) half-change
  if (period != lastKnownPeriod) {
    if (period == 3) {
      Serial.println("⏱️ 2nd Half Started");
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("🏀 2nd Half Started");
      delay(2000);
    }
    lastKnownPeriod = period;
  }

  // (4) game over
  if (strstr(statusText, "Final") && !gameOverAnnounced) {
    Serial.println("🏁 Game Over!");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("🏁 Game Over!");
    delay(2000);
    gameOverAnnounced = true;
  }

  // (5) update LCD
  String cleanDesc = filterToAscii(desc);
  updateScoreLCD(homeTeam, scoreHome, awayTeam, scoreAway, cleanDesc.c_str(), clock, period);


  // (6) decide animation
  bool isThreePointer = doc["isThreePoint"] | false;


  if (madeShot && isDunk) {
    Serial.println("💥 Made DUNK detected! Triggering dunk animation.");
    playDunkAnimation(strip);
  } else if (madeShot && isThreePointer) {
    Serial.println("🎯 Made 3-Point Shot! Running 3pt animation.");
    threePointMadeAnimation(x, y);
  } else {
    flashShot(x, y, result);
  }

  // (7) notify server to pop shot
  popShot(shotIndex);

  // (8) serial log
  Serial.print("🏀 ");
  Serial.print(player);
  Serial.print(" (");
  Serial.print(team);
  Serial.print(") ");
  Serial.print(result);
  Serial.print(" at (");
  Serial.print(x);
  Serial.print(", ");
  Serial.print(y);
  Serial.print(") Score: ");
  Serial.print(scoreAway);
  Serial.print(" - ");
  Serial.print(scoreHome);
  Serial.print(" | ");
  Serial.print(awayTeam);
  Serial.print(" vs ");
  Serial.println(homeTeam);
}

void handleNFLPlay(const JsonDocument& doc) {
  int idx = doc["index"];
  if (idx <= lastShotIndex) return;
  lastShotIndex = idx;


  const char* text = doc["text"] | "";
  int period = doc["period"] | 1;
  const char* clock = doc["clock"] | "";


  Serial.print("🏈 Q");
  Serial.print(period);
  Serial.print(" ");
  Serial.print(clock);
  Serial.print(" - ");
  Serial.println(text);


  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Q");
  lcd.print(period);
  lcd.print(" ");
  lcd.print(clock);
  lcd.setCursor(0, 1);
  for (int i = 0; i < 20 && text[i]; i++) {
    lcd.print(text[i]);
  }
}


void fetchNextShot() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("🚫 WiFi not connected. Skipping fetch.");
    return;
  }


  HttpClient client = HttpClient(wifiClient, serverAddress, port);
  String path = String("/nba/next_shot?client_id=") + client_id;
  Serial.print("Request path: ");
  Serial.println(path);


  int err = client.get(path);


  if (err != 0) {
    Serial.print("❌ HTTP connection failed. Error: ");
    Serial.println(err);
    client.stop();
    delay(1000);  // Wait and try again later
    return;
  }


  int statusCode = client.responseStatusCode();
  if (statusCode == 204) {
    Serial.println("⏳ No new shots yet (204).");
    client.stop();
    delay(1500);  // Slower polling while paused
    return;
  } else if (statusCode != 200) {
    Serial.print("❌ Unexpected HTTP status: ");
    Serial.println(statusCode);
    client.stop();
    delay(1000);
    return;
  }


  String response = client.responseBody();
  client.stop();


  if (response.length() == 0) {
    Serial.println("❌ Empty response body.");
    return;
  }


  StaticJsonDocument<512> doc;
  DeserializationError jsonErr = deserializeJson(doc, response);


  if (jsonErr) {
    Serial.print("❌ JSON Parse error: ");
    Serial.println(jsonErr.c_str());
    return;
  }


  handleShot(doc);
}
