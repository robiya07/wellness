from rest_framework import serializers


class CookingStepSerializer(serializers.Serializer):
    step_number = serializers.IntegerField()
    description = serializers.CharField()


class CookingProcessSerializer(serializers.Serializer):
    steps = CookingStepSerializer(many=True)
    difficulty = serializers.CharField(max_length=50)
    duration = serializers.CharField(max_length=50)


class PortionSerializer(serializers.Serializer):
    weight = serializers.CharField(max_length=100)
    quantity = serializers.CharField(max_length=100)


class NutritionSerializer(serializers.Serializer):
    calories = serializers.CharField(max_length=50)
    proteins = serializers.CharField(max_length=50)
    fats = serializers.CharField(max_length=50)
    carbohydrates = serializers.CharField(max_length=50)


class DishAnalysisSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField()
    kitchen = serializers.CharField(max_length=100, allow_blank=True, allow_null=True)
    ingredients = serializers.ListField(child=serializers.CharField(max_length=255))
    cooking_process = CookingProcessSerializer()
    portion = PortionSerializer()
    nutrition = NutritionSerializer()
    recommendations = serializers.ListField(
        child=serializers.CharField(max_length=500)
    )


class ImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()

    class Meta:
        fields = ['image']
