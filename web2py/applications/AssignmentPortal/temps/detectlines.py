import cv2
import numpy as np

image_name=raw_input("Enter image name: ")
img = cv2.imread(image_name)
gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
edges = cv2.Canny(gray,50,150,apertureSize = 3)

lines = cv2.HoughLines(edges,1,np.pi/180,35)
print type(lines[0])

for rho,theta in lines[0]:
    if(((theta*180)/np.pi)<10):
        if(((theta*180)/np.pi)>1):
            continue
    else:
        if(((theta*180)/np.pi)>89) and (((theta*180)/np.pi)<91):
            pass
        else:
            continue
    print rho,((theta*180)/np.pi)
    a = np.cos(theta)
    b = np.sin(theta)
    x0 = a*rho
    y0 = b*rho
    x1 = int(x0 + 1000*(-b))
    y1 = int(y0 + 1000*(a))
    x2 = int(x0 - 1000*(-b))
    y2 = int(y0 - 1000*(a))

    cv2.line(img,(x1,y1),(x2,y2),(0,0,255),2)

cv2.imwrite('output.jpg',img)
print "output image saved in output.jpg"
