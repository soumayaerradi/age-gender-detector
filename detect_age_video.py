# python detect_age_video.py --face face_detector --age age_detector
from imutils.video import VideoStream
import numpy as np
import argparse
import imutils
import time
import cv2
import os

def detect_and_predict_age(frame, faceNet, ageNet, gender_net, minConf=0.5):
    #define the list of age buckets our age buckets our age detector will predict
	AGE_BUCKETS = ["(0-2)", "(4-6)", "(8-12)", "(15-20)", "(25-32)",
		"(38-43)", "(48-53)", "(60-100)"]

    #initialize our result list
	results = []

    #grab the dimensions of the frame and then contruct a blob from it
	(h, w) = frame.shape[:2]
	blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300),
		(104.0, 177.0, 123.0))

    #pass the blob through the network and obtain the face detections
	faceNet.setInput(blob)
	detections = faceNet.forward()

# loop over the detections
	for i in range(0, detections.shape[2]):
		# extract the confidence (i.e., probability) associated with
		# the prediction
		confidence = detections[0, 0, i, 2]
		# filter out weak detections by ensuring the confidence is
		# greater than the minimum confidence
		if confidence > minConf:
			# compute the (x, y)-coordinates of the bounding box for
			# the object
			box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
			(startX, startY, endX, endY) = box.astype("int")
			# extract the ROI of the face
			face = frame[startY:endY, startX:endX]
			# ensure the face ROI is sufficiently large
			if face.shape[0] < 20 or face.shape[1] < 20:
				continue

					# construct a blob from *just* the face ROI
			faceBlob = cv2.dnn.blobFromImage(face, 1.0, (227, 227),
				(78.4263377603, 87.7689143744, 114.895847746),
				swapRB=False)
			# make predictions on the age and find the age bucket with
			# the largest corresponding probability
			ageNet.setInput(faceBlob)
			preds = ageNet.forward()
			i = preds[0].argmax()
			age = AGE_BUCKETS[i]
			ageConfidence = preds[0][i]
			
			alert_underage(age, ageConfidence)
			
			gender_net.setInput(faceBlob)
			gender_preds = gender_net.forward()
			gender_list = ['Male', 'Female']
			gender = gender_list[gender_preds[0].argmax()]
			d = {
				"loc": (startX, startY, endX, endY),
				"age": (age, ageConfidence),
				"gender": (gender)
			}
			#print(d)
			results.append(d)

    # return our results to the calling function
	return results

def alert_underage(age, age_confidence):
    UNDERAGE = ["(0-2)", "(4-6)", "(8-12)"]
    if((age in UNDERAGE) and age_confidence > 0.9):
        print(age, age_confidence)
        print("UNDERAGE!")
	
def get_fromA(data):
	data = data.replace('(','')
	data = data.replace(')','')
	data0 = int(data.split("-")[1])
	data1 = int(data.split("-")[0])
	return (data0+data1)/2

ap = argparse.ArgumentParser()
ap.add_argument("-f", "--face", required=True,
	help="path to face detector model directory")
ap.add_argument("-a", "--age", required=True,
	help="path to age detector model directory")
ap.add_argument("-c", "--confidence", type=float, default=0.5,
	help="minimum probability to filter weak detections")
args = vars(ap.parse_args())

print("[INFO] loading face detector model...")
prototxtPath = os.path.sep.join([args["face"], "deploy.prototxt"])
weightsPath = os.path.sep.join([args["face"],
	"res10_300x300_ssd_iter_140000.caffemodel"])
faceNet = cv2.dnn.readNet(prototxtPath, weightsPath)

print("[INFO] loading age detector model...")
prototxtPath = os.path.sep.join([args["age"], "age_deploy.prototxt"])
weightsPath = os.path.sep.join([args["age"], "age_net.caffemodel"])
ageNet = cv2.dnn.readNet(prototxtPath, weightsPath)

gender_net = cv2.dnn.readNetFromCaffe(
		'/home/pi/StimaAGPubblicitaPython/data/deploy_gender.prototxt', 
		'/home/pi/StimaAGPubblicitaPython/data/gender_net.caffemodel')

print("[INFO] starting video stream...")
vs = VideoStream(src=0).start()
#vs = cv2.VideoCapture('/home/pi/StimaAGPubblicitaPython/videoPro.mp4')
time.sleep(2.0)

while True:
	frame = vs.read()
	#ret, frame = vs.read()
	frame = imutils.resize(frame, width=400)

	results = detect_and_predict_age(frame, faceNet, ageNet, gender_net, 
		minConf=args["confidence"])

	for r in results:
		text = "{}: {:.2f}%, {}".format(r["age"][0], r["age"][1] * 100,r["gender"][0])
		(startX, startY, endX, endY) = r["loc"]
		y = startY - 10 if startY - 10 > 10 else startY + 10
		cv2.rectangle(frame, (startX, startY), (endX, endY),
			(0, 0, 255), 2)
		cv2.putText(frame, text, (startX, y),
			cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)
		
	# show the output frame
	cv2.imshow("Frame", frame)
	key = cv2.waitKey(1) & 0xFF
	
	# if the `q` key was pressed, break from the loop
	if key == ord("q"):
		break
		
cv2.destroyAllWindows()
vs.stop()
