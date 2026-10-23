from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from recipes.models import Recipe
from .models import Review, ReviewImage

# Semua tindakan yang ada dicakupan "Reviews" itu hanya dapat dilakukan oleh akun yang sudah terverifikasi --> @login_required

# Untuk menambahkan review ke suatu menu/resep
@login_required(login_url='main:login')
def add_review(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        images = request.FILES.getlist('images')

        review = Review.objects.create(
            recipe=recipe,
            user=request.user,
            rating=rating,
            comment=comment
        )

        for img in images[:3]:
            ReviewImage.objects.create(review=review, image=img)

    # Kembali ke halaman detail resep tempat form dikirim
    return redirect('recipes:recipe_detail', pk=recipe.pk)

# Untuk mengedit review user tersebut
@login_required(login_url='main:login')
def edit_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id, user=request.user)
    if request.method == 'POST':
        review.rating = request.POST.get('rating', review.rating)
        review.comment = request.POST.get('comment', review.comment)
        review.is_edited = True
        review.save() # Otomatis memperbarui updated_at

        images = request.FILES.getlist('images')
        if images:
            current_count = review.images.count()
            allowed_slots = 3 - current_count
            
            for img in images[:allowed_slots]:
                ReviewImage.objects.create(review=review, image=img)
    # Kembali ke halaman detail resep tempat form dikirim
    return redirect('recipes:recipe_detail', pk=review.recipe.pk)

# Untuk hapus review si user
@login_required(login_url='main:login')
def delete_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id, user=request.user)
    recipe_pk = review.recipe.pk
    review.delete()

    # Kembali ke halaman detail resep tempat form dikirim
    return redirect('recipes:recipe_detail', pk=recipe_pk)