import re

from PIL import Image, ImageFilter

from easytrader import exceptions


def captcha_recognize(img_path):
    import pytesseract

    im = Image.open(img_path).convert("L")
    threshold = 200
    table = []
    for i in range(256):
        if i < threshold:
            table.append(0)
        else:
            table.append(1)

    out = im.point(table, "1")
    num = pytesseract.image_to_string(out)
    return num


def recognize_verify_code(image_path, broker="ht"):
    """识别验证码，返回识别后的字符串，使用 tesseract 实现
    :param image_path: 图片路径
    :param broker: 券商 ['ht', 'yjb', 'gf', 'yh', 'yh_client', 'gj', 'gj_client']
    :return recognized: verify code string"""

    if broker in ("gf", "gf_client"):
        return detect_gf_result(image_path)
    if broker in ("yh", "yh_client", "gj", "gj_client"):
        return detect_yh_gj_result(image_path)
    return default_verify_code_detect(image_path)


def detect_yh_gj_result(image_path):
    """银河/国金验证码本地 OCR 识别，带图像预处理"""
    from PIL import Image as PilImage

    img = PilImage.open(image_path).convert("L")
    # 二值化：去除浅色背景
    threshold = 140
    img = img.point(lambda p: 255 if p > threshold else 0)
    # 去噪：中值滤波
    img = img.filter(ImageFilter.MedianFilter(size=3))
    return invoke_tesseract_to_recognize(img)


def default_verify_code_detect(image_path):
    from PIL import Image as PilImage

    img = PilImage.open(image_path)
    return invoke_tesseract_to_recognize(img)


def detect_gf_result(image_path):
    from PIL import ImageFilter, Image as PilImage

    img = PilImage.open(image_path)
    if hasattr(img, "width"):
        width, height = img.width, img.height
    else:
        width, height = img.size
    for x in range(width):
        for y in range(height):
            if img.getpixel((x, y)) < (100, 100, 100):
                img.putpixel((x, y), (256, 256, 256))
    gray = img.convert("L")
    two = gray.point(lambda p: 0 if 68 < p < 90 else 256)
    min_res = two.filter(ImageFilter.MinFilter)
    med_res = min_res.filter(ImageFilter.MedianFilter)
    for _ in range(2):
        med_res = med_res.filter(ImageFilter.MedianFilter)
    return invoke_tesseract_to_recognize(med_res)


def invoke_tesseract_to_recognize(img):
    import pytesseract

    try:
        res = pytesseract.image_to_string(img)
    except FileNotFoundError:
        raise Exception(
            "tesseract 未安装，请至 https://github.com/tesseract-ocr/tesseract/wiki 查看安装教程"
        )
    valid_chars = re.findall("[0-9a-z]", res, re.IGNORECASE)
    return "".join(valid_chars)
