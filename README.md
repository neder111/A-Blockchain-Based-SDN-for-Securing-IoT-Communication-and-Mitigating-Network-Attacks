
# SDN-Based IoT Security Framework using Blockchain and AI

This project provides an SDN-based architecture to secure IoT communications using AI-based intrusion detection and blockchain for integrity. The environment includes Mininet, Ryu controller, Flask web apps, and MQTT/CoAP protocols for IoT data transfer.

---

## 🔧 Installation (Ubuntu)

### Install Mininet and Ryu:

```bash
sudo apt-get update
sudo apt-get install mininet
sudo apt-get install python3-ryu
```

Verify installation:

```bash
sudo mn --version
ryu-manager --version
```

---

## 📁 Project Structure

### I) Folders and Files

- `blockchain/`  
  Contains blockchain-related logic and smart contracts (files not specified here).

- `mininet/`  
  Contains Mininet topology and CoAP simulation scripts:
  ```
  tt64.py
  tl64.py
  tm64.py
  ts64.py
  coap_server.py
  coap_publisher.py
  coap_subscriber.py
  ```

- `controller/`  
  Contains SDN controllers and Flask APIs:
  ```
  flask_app_BC.py
  flask_app_NT.py
  controller_NT.py
  controller_BC.py
  generate_keys.py
  ```

- `templates/`  
  HTML templates used by Flask:
  ```
  index.html
  main.html
  ```

---

## 🧪 II) Instructions

### ▶️ A. Running without Blockchain (NT):

1. Open **3 terminals** in the `controller` folder:
    ```bash
    python3 generate_keys.py
    ryu-manager controller_NT.py
    python3 flask_app_NT.py
    ```

2. Open a browser and navigate to:
    ```
    http://127.0.0.1:5000
    or
    http://10.0.2.15:5000
    ```

3. Open a terminal in the `mininet` folder and run:
    ```bash
    sudo python3 tt64.py
    ```

---

### 🔐 B. Running with Blockchain (BC):

1. Open **3 terminals** in the `controller` folder:
    ```bash
    python3 generate_keys.py
    ryu-manager controller_BC.py
    python3 flask_app_BC.py
    ```

2. Open a browser and navigate to:
    ```
    http://127.0.0.1:5000
    or
    http://10.0.2.15:5000
    ```

3. Open a terminal in the `mininet` folder and run:
    ```bash
    sudo python3 tt64.py
    ```

---

## 📡 III) Protocol Instructions

### 1) MQTT Case:

a. In Mininet, launch terminals:
```bash
xterm h1 h1 h2
```

b. In `h1`, run MQTT broker:
```bash
mosquitto -v
```

c. In `h1`, simulate IoT device publishing:
```bash
while true; do 
  mosquitto_pub -h 10.0.0.1 -p 1883 -t iot/dev1 -m "temp: $(shuf -i 25-30 -n 1) hum: $(shuf -i 50-90 -n 1)" 
  sleep 1
done
```

d. In `h2`, subscribe to topic:
```bash
mosquitto_sub -h 10.0.0.1 -p 1883 -t iot/dev1
```

---

### 2) CoAP Case:

a. In Mininet:
```bash
xterm h1 h1 h2
```

b. In `h1`, run server:
```bash
python3 coap_server.py
```

c. In `h1`, run publisher:
```bash
python3 coap_publisher.py
```

d. In `h2`, run subscriber:
```bash
python3 coap_subscriber.py
```

---

### 3) DDoS Attack Simulation:

In Mininet:
```bash
xterm h3
```

In `h3`, run:
```bash
hping3 -s -v -d 120 -w 64 -p 1883 --rand-source --flood 10.0.0.1
```

---

### 4) ARP Spoofing Attack Simulation:

In Mininet:
```bash
xterm h4
```

In `h4`, run:
```bash
ettercap -T -i h4-eth0 -w test.pcap -M ARP /10.0.0.1// /10.0.0.2//
```

---

## ✅ Notes

- Ensure `mosquitto` and `ettercap` are installed:
```bash
sudo apt install mosquitto
sudo apt install ettercap-text-only
```

- Install hping3 if not available:
```bash
sudo apt install hping3
```

---

## 📌 Authors

- Neder Karmous  
- For academic use in IoT-SDN security and smart network experiments.

---

## 📜 License

This project is under MIT License.
