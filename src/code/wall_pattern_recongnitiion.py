import cv2 as cv
import math
import numpy as np
import time
import pymurapi as mur
import glob
import os


""" Класс, предназначенный для обработки изображения с камеры и классификации видов наростов """
class Classifier(object):
	FONT = cv.FONT_HERSHEY_SIMPLEX
	LINE_COLOR = (0,100,255)
	BLACK = ((29, 0, 0), (179, 180, 184))
	COLORS = ((0, 71, 97), (81, 255, 255)) # основные цвета 
	frame = None

	def __init__(self) -> None:
		pass

	""" Определяем вид фигуры """
	def get_enclosing_figure(self, c, cont_area) -> dict:
		# Описанная окружность.
		(_, _), circle_radius = cv.minEnclosingCircle(c)
		circle_area = circle_radius ** 2 * math.pi
		# Описанный эллипс
		try:
			ellipse = cv.fitEllipse(c)
			(_, _), (ellipse_h, ellipse_w), ellipse_angle = ellipse
			ellipse_area = math.pi * (ellipse_h / 2) * (ellipse_w / 2)
		except:
			ellipse = None
			ellipse_area = 0
		# Описанный прямоугольник (с вращением)
		rectangle = cv.minAreaRect(c)
		# Получим контур описанного прямоугольника
		box = cv.boxPoints(rectangle)
		box = np.intp(box)
		# Вычислим площадь и соотношение сторон прямоугольника.
		rectangle_area = cv.contourArea(box)
		# Описанный треугольник
		try:
			triangle = cv.minEnclosingTriangle(c)[1]
			triangle = np.intp(triangle)
			triangle_area = cv.contourArea(triangle)
		except:
			triangle_area = 0
		# Заполним словарь, который будет содержать площади каждой из описанных фигур
		shapes_areas = {
				'Shellfish': min(circle_area, ellipse_area),
				'Corrosion': rectangle_area,
				'Algae': triangle_area,
		}
		# Теперь заполним аналогичный словарь, который будет содержать
		# разницу между площадью контора и площадью каждой из фигур.
		diffs = {
			name: abs(cont_area - shapes_areas[name]) for name in shapes_areas
		}
		# Получаем имя фигуры с наименьшей разницой площади.
		return {
						"cont": c,
						"type": min(diffs, key=diffs.get)
					}
		
	""" Фильтраця по цветам """
	def get_mask(self, frame: np.ndarray) -> np.ndarray:
		mask1 = cv.inRange(frame, self.COLORS[0], self.COLORS[1]) # маска для основных цветов
		mask2 = cv.inRange(frame, self.BLACK[0], self.BLACK[1]) # маска для черных объектов
		return cv.bitwise_or(mask1, mask2)  # черно-белая маска

	""" Выделение контуров """
	def find_contours(self, _frame: np.ndarray, return_mask: bool=False) -> np.ndarray:
		frame = _frame.copy()
		frame = self.contrast(frame)
		hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
		mask = self.get_mask(hsv)
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
				return (None, None)

	""" Увеличение контрастности изображения """
	def contrast(self, img):
		return cv.convertScaleAbs(img, alpha=1.5, beta=40)
	
	"""" Разделение контуров на группы """
	def create_clasters(self, shapes: dict) -> np.ndarray:
		clasters = []
		for figs in shapes.values():
			figs = sorted(figs, key=lambda x: math.dist((0, 0), x[1]))
			cl = [figs.pop(0)]
			for i, fig in enumerate(figs):
				dist = min([math.dist(fig[1], p[-1]) for p in cl])
				if dist < 130:
					cl.append(fig)
				else:
					clasters.append(cl)
					cl = [fig]
				if i == len(figs) - 1:
					clasters.append(cl)
		return clasters

	""" обводка групп обрастаний """
	def draw_clasters_border(self, frame: np.ndarray, clasters: list) -> tuple:
		claster_counts = {}
		for cl in clasters:
			type = cl[0][0]["type"]
			# подсчет кластеров
			if claster_counts.get(type, None) is None:
				claster_counts[type] = 1
			else:
				claster_counts[type] += 1
			# обводка кластеров
			all_points = np.vstack([fig[0]["cont"] for fig in cl])
			x, y, w, h = cv.boundingRect(all_points)
			cv.rectangle(frame, (x - 10, y - 10), (x + w + 10, y + h + 10), (0, 0, 255), 2)
			type = cl[0][0]["type"]
			cv.putText(frame, type, (x, y-9), self.FONT, 0.5, (0, 0, 0), 3, cv.LINE_AA)
			cv.putText(frame, type, (x, y-9), self.FONT, 0.5, (255,255,255), 2, cv.LINE_AA)	
		return frame, claster_counts
	
	""" Рисует на экране данные о типах обрастаний """
	def draw_outgrowts_counts(self, frame: np.ndarray, counts: dict) -> np.ndarray:
		front, back = [10, 30], [10, 30]
		for type, count in counts.items():
			text = f"{type}: {count}"
			cv.putText(frame, text, back, self.FONT, 0.65, (0, 0, 0), 5, cv.LINE_AA)
			cv.putText(frame, text, front, self.FONT, 0.65, (255, 255, 255), 2, cv.LINE_AA)
			front[1] += 25
			back[1] += 25
		return frame

	""" Получение словаря вида {тип обрастания: [фигура, центр]} """
	def get_shapes_dict(self, objects: list) -> dict:
		l = {}
		for fig, center in objects:
			if l.get(fig['type']) == None:
				l[fig['type']] = [(fig, center)]
			else:
				l[fig['type']].append((fig, center))
		return l
	
	""" Сохранение картинки """
	def make_screenshot(self, frame: np.ndarray) -> np.ndarray:
		filename = time.strftime('%H-%M-%S', time.localtime(time.time()))+".png"
		path = os.path.join(os.getcwd(), "WRS", "final", "assets", filename)
		print(f"Screenshot saved: {path}")
		cv.imwrite(path, frame)
		cv.imshow("screenshot", cv.imread(path))
		cv.waitKey(0)

	""" Посик повреждений на судне """
	def detect_outgrowth(self, frame: np.ndarray) -> tuple:
		original_frame = frame
		h,  w = frame.shape[:2]
		frame = cv.bilateralFilter(frame, 9, 75, 75)[100:h-75, 25:w-25]
		frame = cv.dilate(frame, np.ones((5,5),np.uint8), iterations=1)
		cont, mask = self.find_contours(frame, return_mask=True)
		objects = []
		for c in cont:
			area = cv.contourArea(c)
			if area < 200:
				continue
			figure = self.get_enclosing_figure(c, area)
			center = self.get_contour_center(c)
			objects.append([figure, center])
		
		shapes_dict = self.get_shapes_dict(objects)
		clasters = self.create_clasters(shapes_dict)
		frame, claster_counts = self.draw_clasters_border(frame, clasters)
		self.draw_outgrowts_counts(frame, claster_counts)
		
		return original_frame, frame, mask


""" Запуск на аппарате """	
if __name__ == "__main__":
	start_time = time.time()
	auv = mur.mur_init()
	classifier = Classifier()

	cap = cv.VideoCapture('http://10.42.0.100/mjpeg')
	while True:
		ok, frame = cap.read()
		if not ok:
			print("Can't receive frame")
			cv.waitKey(1000)
		else:
			original_frame, frame, mask = classifier.detect_outgrowth(frame)
			cv.imshow("Original", original_frame)
			cv.imshow("Edited", frame)
			# cv.imshow("Mask", mask)

			key = cv.waitKey(1)
			if key == 27: # нажат escape
				exit()
			elif key == 49: # нажата 1
				print("Making screenshot")
				classifier.make_screenshot(frame)

