from fastapi import FastAPI,  HTTPException
from datetime import datetime
import threading, time, json, uvicorn, paho.mqtt.client as mqtt
import os
from dotenv import load_dotenv
load_dotenv()

mqtt_username=os.getenv('mqtt_username')
mqtt_password=os.getenv('mqtt_password')
client_id=os.getenv('client_id')
mqtt_broker=os.getenv('mqtt_broker')
mqtt_port=1883
ip=os.getenv('ip')

app = FastAPI(title="Onwords Master API",description="Only API for accessing all Onword's Devices !",version="1.0.0",docs_url="/",openapi_url="/openapi.json", redoc_url=None,debug=True)

@app.get("/Get_Device_Status/{product_id}/{device_id}",operation_id="get status of single device",tags=["Status Management"])
async def get_a_devices_status(product_id: str,device_id:str):
    try:
        status=[]
        def on_connect(client, userdata, flags, rc):
            # subscribing to the product topic
            device_data = f"onwords/{product_id}/status"
            client.subscribe(device_data)
            request_data = {"request": "getCurrentStatus"}
            request_payload = json.dumps(request_data)
            # publishing the message
            client.publish(f"onwords/{product_id}/getCurrentStatus", payload=request_payload, qos=1)

        def on_message(client, userdata, msg):
            try:
                original_bytes = msg.payload.decode('utf-8')
                cleaned_string = original_bytes
                status.append(cleaned_string)

            except Exception as e:
                print("Error processing message:", e)
        
        client = mqtt.Client(client_id)
        client.on_connect = on_connect
        client.on_message = on_message
        client.username_pw_set(username=mqtt_username, password=mqtt_password)
        client.connect(mqtt_broker, mqtt_port, keepalive=60)
        client.loop_start()
        client.loop_stop()
        client.disconnect()
        return status

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 

@app.post("/Change_device_status/{product_id}/{device_id}/{power_state_value}",operation_id="Change status of a single device using this Method",tags=["Status Management"],summary="change the status of a device")
async def change_device_status (product_id: str, device_id: str, power_state_value: str):
    try:
        status = []
        def on_connect(client, userdata, flags, rc):
            # subscribing to the device topics like its current topic 
            device_data = f"onwords/{product_id}/status"
            client.subscribe(device_data)
            request_data = {'request':'getCurrentStatus'}
            request_payload = json.dumps(request_data)
            client.publish(f"onwords/{product_id}/getCurrentStatus", payload=request_payload, qos=1)
        
        def on_message(client, userdata, msg):
            print('Recived message')
            try:
                original_bytes = msg.payload.decode('utf-8')
                cleaned_string = original_bytes
                status.append(cleaned_string)
            except Exception as e:
                print("Error in master api , change device status function = ", e)
        
        client = mqtt.Client(client_id)
        client.on_connect = on_connect
        client.on_message = on_message
        client.username_pw_set(username=mqtt_username, password=mqtt_password)
        client.connect(mqtt_broker, mqtt_port, keepalive=60)
        client.loop_start()
        client.loop_stop()
        client.disconnect()

        response_dict = json.loads(status[0])
        if product_id.startswith('3chag'):
            response_dict = {'action':"doubleGate"}
        else:
            response_dict[device_id] = power_state_value
        request_payload = json.dumps(response_dict)

        def on_connect(client, userdata, flags, rc):
            client.publish(f"onwords/{product_id}status", payload = request_payload, qos=1, retain=False)
            client.disconnect()
        
        client = mqtt.Client()
        client = mqtt.Client(client_id)
        client.on_connect = on_connect
        client.username_pw_set(username=mqtt_username, password=mqtt_password)
        client.connect(mqtt_broker, mqtt_port, keepalive=60)
        client.loop_forever()
        return {'message':"Device status changed successfully"}
            
    except Exception as e:
        print("Error = master api error in change_device_status function ", e)
        raise HTTPException(status_code=400, detail=str(e))
    
@app.post("/Change_Fan_Speed/{product_id}/{device_id}/{range_value}",operation_id="change fan speed using this Method",tags=["Status Management"],summary="change the mode a of device")
async def change_device_speed (product_id: str, device_id: str, range_value: str):
    try:
        status = []
        def on_connect (client, userdata, flags, rc):
            device_data = f"onwords/{product_id}/status"
            client.subscribe(device_data)
            request_data = {'request':'getCurrentStatus'}
            request_payload = json.dumps(request_data)
            client.publish(f'onwords/{product_id}/getCurrentStatus', payload=request_payload, qos=1)
        
        def on_message(client, userdata,msg):
            try:
                original_bytes = msg.payload.decode('utf-8')
                cleaned_string = original_bytes
                status.append(cleaned_string)
            except Exception as e:
                print('Error = ', e)
        client = mqtt.Client(client_id)
        client.on_connect = on_connect
        client.on_message = on_message
        client.username_pw_set(username=mqtt_username, password=mqtt_password)
        client.connect(mqtt_broker, mqtt_port, keepalive=60)
        client.loop_start()
        client.loop_stop()
        client.disconnect()
        response_dict = json.loads(status[0])

        if product_id.startswith('4ch'):
            response_dict['speed'] = range_value
        
        request_payload = json.dumps(response_dict)

        def on_connect(client, userdata, flags, rc):
            client.publish(f"onwords/{product_id}/status", payload=request_payload, qos=1, retain=False)
            client.disconnect()
        client = mqtt.Client()
        client = mqtt.Client(client_id)
        client.on_connect = on_connect
        client.username_pw_set(username=mqtt_username, password=mqtt_password)
        client.connect(mqtt_broker, mqtt_port, keepalive=60)
        client.loop_forever()
        return {'message':"Device Status change successfully"}

    except Exception as e:
        print("error in master api change device speed function = ", e)
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
        


        