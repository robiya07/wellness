import re
import google.generativeai as genai
from PIL import Image
from io import BytesIO

from django.conf import settings
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from shared.serializers import ImageUploadSerializer, DishAnalysisSerializer


class DishAnalysisView(generics.GenericAPIView):
    serializer_class = ImageUploadSerializer
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image_file = serializer.validated_data['image']

        try:
            dish_data = self.analyze_dish_with_gemini(image_file)

            response_serializer = DishAnalysisSerializer(data=dish_data)
            response_serializer.is_valid(raise_exception=True)

            return Response(response_serializer.validated_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def analyze_dish_with_gemini(self, image_file):
        genai.configure(api_key=settings.GEMINI_API_KEY)

        image_bytes = BytesIO(image_file.read())
        image = Image.open(image_bytes)

        model = genai.GenerativeModel('gemini-1.5-flash')

        prompt = """Проанализируй изображение блюда и предоставь точную структурированную информацию по шаблону:
##БЛЮДО##
НАЗВАНИЕ: [короткое название блюда]
ОПИСАНИЕ: [1 предложение о вкусе, текстуре и основных особенностях]
КУХНЯ: [страна/регион происхождения, если определимо]
##ИНГРЕДИЕНТЫ##
- [основной ингредиент] 
- [второй ингредиент]
- [остальные ингредиенты]
##ПРИГОТОВЛЕНИЕ##
1. [первый шаг приготовления]
2. [второй шаг приготовления]
3. [дополнительные шаги]
СЛОЖНОСТЬ: [Легкая/Средняя/Высокая]
ВРЕМЯ: [приблизительное время в минутах]
##ИНФОРМАЦИЯ О ПОРЦИИ##
ВЕС: [диапазон в граммах]
КОЛИЧЕСТВО: [на сколько человек рассчитано]
##ПИЩЕВАЯ ЦЕННОСТЬ##
КАЛОРИИ: [XX-YY] ккал
БЕЛКИ: [XX-YY] г
ЖИРЫ: [XX-YY] г
УГЛЕВОДЫ: [XX-YY] г
##РЕКОМЕНДАЦИИ##
[1-2 кратких совета по подаче или сочетанию с другими блюдами]
Отвечай строго по этому шаблону без приветствий и вводного текста. Сохраняй форматирование с разделителями ##РАЗДЕЛ##. Все поля обязательны."""

        response = model.generate_content([prompt, image])

        return self.parse_gemini_response(response.text)

    def parse_gemini_response(self, response_text):
        result = {
            "name": "",
            "description": "",
            "kitchen": "",
            "ingredients": [],
            "cooking_process": {
                "steps": [],
                "difficulty": "",
                "duration": ""
            },
            "portion": {
                "weight": "",
                "quantity": ""
            },
            "nutrition": {
                "calories": "",
                "proteins": "",
                "fats": "",
                "carbohydrates": ""
            },
            "recommendations": []
        }

        dish_pattern = r'##БЛЮДО##\s+НАЗВАНИЕ:\s+(.*?)\s+ОПИСАНИЕ:\s+(.*?)\s+КУХНЯ:\s+(.*?)\s+##'
        dish_match = re.search(dish_pattern, response_text, re.DOTALL)
        if dish_match:
            result["name"] = dish_match.group(1).strip()
            result["description"] = dish_match.group(2).strip()
            result["kitchen"] = dish_match.group(3).strip()

        ingredients_pattern = r'##ИНГРЕДИЕНТЫ##\s+(.*?)##ПРИГОТОВЛЕНИЕ##'
        ingredients_match = re.search(ingredients_pattern, response_text, re.DOTALL)
        if ingredients_match:
            ingredients_text = ingredients_match.group(1)
            ingredient_lines = [line.strip() for line in ingredients_text.strip().split('\n') if line.strip()]
            result["ingredients"] = [line.replace('- ', '') for line in ingredient_lines]

        cooking_pattern = r'##ПРИГОТОВЛЕНИЕ##\s+(.*?)СЛОЖНОСТЬ:\s+(.*?)\s+ВРЕМЯ:\s+(.*?)\s+##'
        cooking_match = re.search(cooking_pattern, response_text, re.DOTALL)
        if cooking_match:
            steps_text = cooking_match.group(1).strip()
            difficulty = cooking_match.group(2).strip()
            duration = cooking_match.group(3).strip()

            step_lines = [line.strip() for line in steps_text.split('\n') if line.strip() and re.match(r'^\d+\.', line)]
            steps = []
            for i, step in enumerate(step_lines):
                step_text = re.sub(r'^\d+\.\s*', '', step)
                steps.append({"step_number": i + 1, "description": step_text.strip()})

            result["cooking_process"] = {
                "steps": steps,
                "difficulty": difficulty,
                "duration": duration
            }

        portion_pattern = r'##ИНФОРМАЦИЯ О ПОРЦИИ##\s+ВЕС:\s+(.*?)\s+КОЛИЧЕСТВО:\s+(.*?)\s+##'
        portion_match = re.search(portion_pattern, response_text, re.DOTALL)
        if portion_match:
            result["portion"] = {
                "weight": portion_match.group(1).strip(),
                "quantity": portion_match.group(2).strip()
            }

        nutrition_pattern = r'##ПИЩЕВАЯ ЦЕННОСТЬ##\s+КАЛОРИИ:\s+(.*?)\s+БЕЛКИ:\s+(.*?)\s+ЖИРЫ:\s+(.*?)\s+УГЛЕВОДЫ:\s+(.*?)\s+##'
        nutrition_match = re.search(nutrition_pattern, response_text, re.DOTALL)
        if nutrition_match:
            result["nutrition"] = {
                "calories": nutrition_match.group(1).strip(),
                "proteins": nutrition_match.group(2).strip(),
                "fats": nutrition_match.group(3).strip(),
                "carbohydrates": nutrition_match.group(4).strip()
            }

        recommendations_pattern = r'##РЕКОМЕНДАЦИИ##\s+(.*?)$'
        recommendations_match = re.search(recommendations_pattern, response_text, re.DOTALL)
        if recommendations_match:
            recs_text = recommendations_match.group(1).strip()
            result["recommendations"] = [recs_text]
            if '\n' in recs_text:
                result["recommendations"] = [rec.strip().replace('- ', '') for rec in recs_text.split('\n') if
                                             rec.strip()]

        return result
