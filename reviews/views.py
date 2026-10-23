from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from recipes.models import Recipe
from .models import Review

# Semua tindakan yang ada dicakupan "Reviews" itu hanya dapat dilakukan oleh akun yang sudah terverifikasi --> @login_required

# Untuk menambahkan review ke suatu menu/resep
@login_required(login_url='main:login')
def add_review(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    if request.method == 'POST':
        rating = int(request.POST.get('rating', 0))
        comment = request.POST.get('comment', '').strip()
        image = request.FILES.get('image')  # Ambil foto jika usernya meng-upload
        
        if 1 <= rating <= 5:
            Review.objects.create(
                recipe=recipe,
                user=request.user,
                rating=rating,
                comment=comment,
                image=image
            )
    # Kembali ke halaman detail resep tempat form dikirim
    return redirect('recipes:recipe_detail', pk=recipe.pk)

# Untuk mengedit review user tersebut
@login_required(login_url='main:login')
def edit_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id, user=request.user)
    recipe_pk = review.recipe.pk # Ambil ID resepnya dulu
    if request.method == 'POST':
        rating = int(request.POST.get('rating', 0))
        comment = request.POST.get('comment', '').strip()
        image = request.FILES.get('image')
        
        if 1 <= rating <= 5:
            review.rating = rating
            review.comment = comment
            if image:
                review.image = image
            review.save()
    # Kembali ke halaman detail resep tempat form dikirim
    return redirect('recipes:recipe_detail', pk=recipe_pk)

# Untuk hapus review si user
@login_required(login_url='main:login')
def delete_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id, user=request.user)
    recipe_pk = review.recipe.pk  # Ambil ID resepnya sebelum ulasannya dihapus
    
    if request.method == 'POST':
        review.delete()

    # Kembali ke halaman detail resep tempat form dikirim
    return redirect('recipes:recipe_detail', pk=recipe_pk)