import cv2
import numpy as np
from shapely.geometry import LineString
from operator import itemgetter

verline=[]#LineString(i for i in vertical_lines)
horline=[]#LineString(i for i in horizontal_lines)

image_name=raw_input("Enter image name: ")
img = cv2.imread(image_name)
gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
edges = cv2.Canny(gray,50,150,apertureSize = 3)

lines = cv2.HoughLines(edges,0.5,(2*(np.pi))/180,45)
vertical_lines=[] #vertical lines
horizontal_lines=[] #horizontal lines
for rho,theta in lines[0]:
    if(((theta*180)/np.pi)<10):
        if(((theta*180)/np.pi)>1):
            continue
    else:
        continue
    cont=0
    if len(vertical_lines)>0:
        for dupl in vertical_lines:
            if abs(rho-dupl[0])<25:
                cont=1
                break
        if cont==1:
            continue
    print "vertical"
    print rho,((theta*180)/np.pi)
    vertical_lines.append([rho,theta])
    a = np.cos(theta)
    b = np.sin(theta)
    x0 = a*rho
    y0 = b*rho
    x1 = int(x0 + 2000*(-b))
    y1 = int(y0 + 2000*(a))
    x2 = int(x0 - 2000*(-b))
    y2 = int(y0 - 2000*(a))
    verline.append([(x1,y1),(x2,y2)])
    #cv2.line(img,(x1,y1),(x2,y2),(0,0,255),2) #too check

del lines
lines = cv2.HoughLines(edges,0.5,(2*(np.pi))/180,200)
for rho,theta in lines[0]:
    if(((theta*180)/np.pi)<30):
        continue
    else:
        if(((theta*180)/np.pi)<89.7) or (((theta*180)/np.pi)>90.3):
            continue
    cont=0
    if len(horizontal_lines)>0:
        for dupl in horizontal_lines:
            if abs(rho-dupl[0])<25:
                cont=1
                break
    if cont==1:
        continue
    print "\nhorizontal"
    print rho,((theta*180)/np.pi)
    horizontal_lines.append([rho,theta])
    a = np.cos(theta)
    b = np.sin(theta)
    x0 = a*rho
    y0 = b*rho
    x1 = int(x0 + 2000*(-b))
    y1 = int(y0 + 2000*(a))
    x2 = int(x0 - 2000*(-b))
    y2 = int(y0 - 2000*(a))
    #cv2.line(img,(x1,y1),(x2,y2),(0,0,255),2) #to check
horizontal_lines = sorted(horizontal_lines,key=itemgetter(0),reverse=True)[0]
theta=horizontal_lines[1]
rho =horizontal_lines[0]
a = np.cos(theta)
b = np.sin(theta)
x0 = a*rho
y0 = b*rho
x1 = int(x0 + 2000*(-b))
y1 = int(y0 + 2000*(a))
x2 = int(x0 - 2000*(-b))
y2 = int(y0 - 2000*(a))
horline.append([(x1,y1),(x2,y2)])
all_points=[]
cv2.imwrite('output.jpg',img)
for i in horline:
    for j in verline:
         temp=(LineString(i).intersection(LineString(j)))
         all_points.append([temp.x,temp.y])
all_points = sorted(all_points,key=itemgetter(0))
c1=0
c2=0
count=1
print all_points
for i in range(len(all_points)):
    print c2,all_points[i][0]
    cropimg=img[c1:all_points[i][1],c2:all_points[i][0]]
    cv2.imwrite("part"+str(i+1)+".jpg", cropimg)
    c2=all_points[i][0]

print img.shape
print all_points[i][0]
cropimg=img[all_points[i][1]:img.shape[0],0:img.shape[1]]
cv2.imwrite("part"+str(i+2)+".jpg", cropimg)
print "output image saved in output.jpg"
