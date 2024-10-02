
from fastapi import FastAPI, HTTPException
import json, asyncio, uvicorn, uuid, paho.mqtt.client as mqtt
import os
from dotenv import load_dotenv
load_dotenv()

mqtt_username = os.getenv('mqtt_username')
mqtt_password = os.getenv('mqtt_password')
client_id = os.getenv('client_id')
mqtt_broker = os.getenv('mqtt_broker')
mqtt_port = 1883

app = FastAPI(title="Onwords Master API (Test)", description="Only API for accessing all Onword's Devices!, This is test version of master api used for testing", version="1.0.0", docs_url="/", openapi_url="/openapi.json", redoc_url=None, debug=True)

def create_mqtt_client(on_connect, on_message):
    client = mqtt.Client(client_id=f"{client_id}_{uuid.uuid4()}")
    client.on_connect = on_connect
    client.on_message = on_message
    client.username_pw_set(username=mqtt_username, password=mqtt_password)
    client.connect(mqtt_broker, mqtt_port, keepalive=60)
    return client

@app.get("/Get_Device_Status/{product_id}/{device_id}", operation_id="get status of single device", tags=["Status Management"])
async def get_a_devices_status(product_id: str, device_id: str):
    try:
        status = []
        status_event = asyncio.Event()

        def on_connect(client, userdata, flags, rc):
            device_data = f"onwords/{product_id}/currentStatus"
            client.subscribe(device_data)
            request_data = {"request": "getCurrentStatus"}
            request_payload = json.dumps(request_data)
            client.publish(f"onwords/{product_id}/getCurrentStatus", payload=request_payload)

        def on_message(client, userdata, msg):
            try:
                original_bytes = msg.payload.decode('utf-8')
                cleaned_string = original_bytes
                status.append(cleaned_string)
                status_event.set()
            except Exception as e:
                print("Error processing message:", e)

        client = create_mqtt_client(on_connect, on_message)
        client.loop_start()

        timeout = 10
        try:
            await asyncio.wait_for(status_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

        client.loop_stop()
        client.disconnect()
        
        # if we got no status then show show default value everything is off
        if not status:
            if product_id.startswith("3chfb"):
                return {f"device{i}": 0 for i in range(1, 4)}
            elif product_id.startswith("3chrb"):
                return {f"device{i}": 0 for i in range(1, 4)}
            elif product_id.startswith("4ch"):
                return {f"device{i}": 0 for i in range(1, 5)}
            elif product_id.startswith("4ltc"):
                return {f"device{i}": 0 for i in range(1, 5)}
            elif product_id.startswith("3l1ftc"):
                return {**{f"device{i}": 0 for i in range(1, 4)}, "device4": {"speed": 0}}

            elif product_id.startswith("4l2ftc"):
                return {**{f"device{i}": 0 for i in range(1, 5)}, "device5": {"speed": 0}, "device6": {"speed_1": 0}}

        #  if we got the status 

        cleaned_status = json.loads(status[0])

        # trying to make the data consistant
        if product_id.startswith("3chfb"):
            for i in range(1, 4):
                if f"device{i}" not in cleaned_status:
                    cleaned_status[f"device{i}"] = 0
        elif product_id.startswith("3chrb"):
            for i in range(1, 4):
                if f"device{i}" not in cleaned_status:
                    cleaned_status[f"device{i}"] = 0
        elif product_id.startswith("4ch"):
            for i in range(1, 5):
                if f"device{i}" not in cleaned_status:
                    cleaned_status[f"device{i}"] = 0
        elif product_id.startswith("4ltc"):
            for i in range(1, 5):
                if f"device{i}" not in cleaned_status:
                    cleaned_status[f"device{i}"] = 0
        elif product_id.startswith("3l1ftc"):
            for i in range(1, 4):
                if f"device{i}" not in cleaned_status:
                    cleaned_status[f"device{i}"] = 0
            if "device4" not in cleaned_status:
                cleaned_status["device4"] = {"speed": 0}
            elif product_id.startswith("4l2ftc"):
                for i in range(1, 5):
                    if f"device{i}" not in cleaned_status:
                        cleaned_status[f"device{i}"] = 0
                if "device5" not in cleaned_status:
                    cleaned_status["device5"] = {"speed": 0}
                if "device6" not in cleaned_status:
                    cleaned_status["device6"] = {"speed_1": 0}

        return cleaned_status

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
device_speeds = {}


@app.post("/Change_device_status/{product_id}/{device_id}/{power_state_value}", operation_id="Change status of a single device using this Method", tags=["Status Management"], summary="change the status of a device")  
async def change_device_status(product_id: str, device_id: str, power_state_value: str):
    try:
        response_dict = {}
        
        try:
            power_state_value = int(power_state_value)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid power_state_value. It must be an integer.")


        # Get the current device status
        current_status = await get_a_devices_status(product_id, device_id)

        # Get the current speed for fan devices
        current_speed = current_status.get("speed", 5) 
        current_speed1 = current_status.get("speed_1", 5) 

        # Logic based on product_id and device_id 
        if product_id.startswith("3ch1frb"):
            if device_id == "device4":  # This is the fan
                response_dict["speed"] = current_speed  # Only add speed for the fan
                response_dict[device_id] = power_state_value
            else:  # This is a light
                response_dict[device_id] = power_state_value

        elif product_id.startswith("3l1ftc"):
            if device_id == "device4":
                response_dict["speed"] = current_speed  # Fan speed
                response_dict[device_id] = power_state_value
            else:  # Lights
                response_dict[device_id] = power_state_value
                
        elif product_id.startswith("4l2ftc"):
            if device_id == "device5":  # Fan 1
                response_dict["speed"] = current_speed
                response_dict[device_id] = power_state_value  
            elif device_id == "device6":  # Fan 2
                response_dict["speed_1"] = current_speed1 
                response_dict[device_id] = power_state_value 
            else:  # Lights
                response_dict[device_id] = power_state_value 

        else:
            response_dict[device_id] = power_state_value 

        # Only retain speed for fan when turning off, not lights
        if power_state_value == 0 and "speed" in response_dict:
            response_dict["speed"] = current_speed  # Retain the fan's current speed
        
        # Add common fields
        response_dict["client_id"] = "Alexa"
        response_dict["ip"] = "13.126.129.54"

        # Prepare and print the payload
        request_payload = json.dumps(response_dict)
        print(f"Prepared payload: {request_payload}")

        # Publish payload to MQTT broker
        def on_connect(client, userdata, flags, rc):
            print(f"Connected to MQTT broker with result code {rc}")
            client.publish(f"onwords/{product_id}/status", payload=request_payload, qos=0, retain=False)
            print(f"Published payload to onwords/{product_id}/status")
            client.disconnect()

        client = create_mqtt_client(on_connect, None)
        client.loop_forever()

        return {"message": "Device Status changed successfully", "payload": response_dict}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    
@app.post("/Change_Fan_Speed/{product_id}/{device_id}/{range_value}", operation_id="change fan speed using this Method", tags=["Status Management"], summary="change the mode a of device")
async def change_device_speed(product_id: str, device_id: str, range_value: str):
    try:
        try:
            range_value = int(range_value)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid range_value. It must be an integer.")

        response_dict = {}

        # this code can cause an inconsistant range (as if the user make the range to 0)
        # this will still make the fan run on speed 1
        response_dict[device_id] = 1

        # for one fan board
        if product_id.startswith("3ch1frb"):
            if device_id == "device4":
                response_dict["speed"] = range_value        
        elif product_id.startswith("3l1ftc"):
            if device_id == "device4":
                response_dict["speed"] = range_value 
        # for two fan board
        elif product_id.startswith("4l2ftc"):
            if device_id == "device5":
                response_dict["speed"] = range_value
            elif device_id == "device6":
                response_dict["speed_1"] = range_value
        else:
            raise HTTPException(status_code=400, detail="Unsupported product_id")

        response_dict["client_id"] = "Alexa"
        response_dict["ip"] = "13.126.129.54"
        request_payload = json.dumps(response_dict)

        print(f"Prepared payload: {request_payload}")

        def on_connect(client, userdata, flags, rc):
            print(f"Connected to MQTT with result code {rc}")
            client.publish(f"onwords/{product_id}/status", payload=request_payload, qos=0, retain=False)
            print(f"Published to topic: onwords/{product_id}/status")
            client.disconnect()

        client = create_mqtt_client(on_connect, None)
        client.loop_forever()

        return {"message": "Device Speed changed successfully", "payload": response_dict}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "_main_":
    uvicorn.run(app, host="0.0.0.0", port=8000)