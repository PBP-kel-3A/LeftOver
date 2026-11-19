from rest_framework import serializers
from .models import Review, ReviewImage


class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ['id', 'image']


class ReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id',
            'recipe',
            'user',
            'username',
            'rating',
            'comment',
            'images',
            'is_edited',
            'created_at',
            'updated_at',
            'time_ago',
        ]
        read_only_fields = ['id', 'user', 'is_edited', 'created_at', 'updated_at']

    def get_time_ago(self, obj):
        return obj.get_time_ago()