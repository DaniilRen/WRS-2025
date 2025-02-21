import cv2 as cv
import math
import numpy as np
import time
import pymurapi as mur
import os


""" Класс, предназначенный для обработки изображения с камеры, поиска и подсчета повреждений """
class Classifier(object):
	FONT = cv.FONT_HERSHEY_SIMPLEX
	LINE_COLOR = (0,100,255)
	HOLE_COLOR = ((0, 71, 97), (86, 255, 255)) # основные цвета
	hole_centers = []
	center_zone_mask = None


	def __init__(self, start_time) -> None:
		self.start_time = start_time

	""" Определяем вид фигуры """
	def get_enclosing_figure(self, c, cont_area) -> dict:
		# Описанный эллипс
		try:
			ellipse = cv.fitEllipse(c)
		except:
			return None
		return {
						"cont": c,
						"ellipse": ellipse
					}

	""" Выделение контуров """
	def find_contours(self, _frame: np.ndarray, return_mask: bool=False) -> np.ndarray:
		frame = _frame.copy()
		frame = cv.bilateralFilter(frame,9, 135, 135)
		gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
		# blur = cv.GaussianBlur(gray, (0,0), sigmaX=33, sigmaY=33)
		blur = cv.Canny(gray,140,225)
		blur = cv.GaussianBlur(blur, (3, 3), 0)
		divide = cv.divide(gray, blur, scale=255)
		thresh = cv.threshold(divide, 205, 255, cv.THRESH_OTSU)[1]
		kernel = cv.getStructuringElement(cv.MORPH_RECT, (3,3))
		mask = cv.morphologyEx(thresh, cv.MORPH_CLOSE, kernel)
		
		cont, _ = cv.findContours(mask, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)
		res = [sorted(cont, key=cv.contourArea, reverse=True)]
		if return_mask:
			res.append(mask)
		return res
	
	""" Возращает центр контура. Если ошибка - None """
	def get_contour_center(self, cont) -> tuple:
		moments = cv.moments(cont)
		try:
			x = int(moments['m10'] / moments['m00'])
			y = int(moments['m01'] / moments['m00'])
			return (x, y)
		except ZeroDivisionError:
				return None

	""" Вывод числа повреждений """
	def draw_holes_counts(self, frame: np.ndarray, count: int) -> np.ndarray:
		text = f"Found: {count}"
		cv.putText(frame, text, [10, 30], self.FONT, 0.65, (0, 0, 0), 5, cv.LINE_AA)
		cv.putText(frame, text, [10, 30], self.FONT, 0.65, (255, 255, 255), 2, cv.LINE_AA)
		return frame
	
	""" Добавление повеждения в список для подсчета """
	def insert_hole_center(self, center_cords: tuple) -> None:
		self.hole_centers.append(center_cords)
		print(f"Inserted №{len(self.hole_centers)} hole: {center_cords}")

	""" Проверка на то, считали ли мы уже повреждение """
	def check_hole_center(self, center_cords: tuple) -> bool:
		for c in self.hole_centers:
			x, y = center_cords
			print(c, (x, y))
			if abs(x-c[0]) <= 30 or abs(y-c[1]) <= 30:
				print(x, y, c, "- Already in array!")
				return False
		self.insert_hole_center(center_cords)
		return True

	""" Рисует рамку вокруг контура """
	def create_border(self, _frame: np.ndarray, figure: dict) -> np.ndarray:
		frame = _frame.copy()
		cv.ellipse(frame, figure["ellipse"], (0, 0, 255), 4)
		return frame	
	
	""" Сохранение картинки """
	def make_screenshot(self, frame: np.ndarray) -> np.ndarray:
		filename = time.strftime('%H-%M-%S', time.localtime(time.time()))+"_hole.png"
		path = os.path.join(os.getcwd(), "WRS", "final", "assets", filename)
		print(f"Saved to: {path}")
		cv.imwrite(path, frame)
		cv.imshow("screenshot", cv.imread(path))
		cv.waitKey(0)

	""" Круговая зона в середине экрана """
	def create_center_zone(self, frame: np.ndarray, center_cords: tuple) -> np.ndarray:
		mask = np.zeros_like(frame)
		mask = cv.cvtColor(mask, cv.COLOR_BGR2GRAY)
		mh, mw = mask.shape[:2]
		cv.circle(mask, (mw//2, mh//2), 20, (255, 255, 255), -1, cv.LINE_AA)
		# self.draw_object_center(mask, center_cords)
		self.center_zone_mask = mask
		return mask	

	""" Проверка для отверстия в конце трубы """
	def in_active_zone(self, frame: np.ndarray, cont: np.ndarray, center_cords: tuple) -> np.ndarray:
		mask = self.create_center_zone(frame, center_cords)
		mask_cont, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
		return cv.pointPolygonTest(mask_cont[0], center_cords, False) in [1, 0] and 300 <= cv.contourArea(cont) <= 2700
	
	""" Отсеивание лишних контуров """
	def check_contour(self, frame: np.ndarray, cont: np.ndarray) -> bool:
		center = self.get_contour_center(cont)
		if center is None:
			return 0
		return self.in_active_zone(frame, cont, center) or 300 <= cv.contourArea(cont) <= 3000

	""" Посик отверстий в трубе """
	def detect_holes(self, frame: np.ndarray) -> tuple:
		original_frame = frame
		cont, mask = self.find_contours(frame, return_mask=True)
		count = 0
		cont = filter(lambda c: self.check_contour(frame, c), cont)
		cont = sorted(cont, key=cv.contourArea)
		for c in cont:
			area = cv.contourArea(c)
			count += 1
			ellipse = self.get_enclosing_figure(c, area)
			if ellipse == None:
				continue
			center = self.get_contour_center(c)
			if center is None:
				continue
			frame = self.create_border(frame, ellipse)
			self.check_hole_center(center)
		
		self.draw_holes_counts(frame, len(self.hole_centers))
		return original_frame, frame, mask, self.center_zone_mask


""" Запуск на аппарате """	
if __name__ == "__main__":
	start_time = time.time()
	auv = mur.mur_init()
	classifier = Classifier(start_time)

	cap = cv.VideoCapture('http://10.42.0.100/mjpeg')
	while True:
		ok, ret = cap.read()
		if ok:
			original_frame, frame, mask, center_mask = classifier.detect_holes(ret)
			cv.imshow("Original", original_frame)
			cv.imshow("Edited", frame)
			# cv.imshow("Mask", mask)
			# cv.imshow("Center mask", center_mask)
		key = cv.waitKey(1)
		if key == 27: # нажат escape
			exit()
		elif key == 49: # нажата 1
			print("Making screenshot")
			classifier.make_screenshot(frame)
