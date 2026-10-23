from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.loader import render_to_string
from recipes.models import Recipe
from .models import Review, ReviewImage

# Semua tindakan di cakupan "Reviews" hanya bisa dilakukan akun yang sudah login --> @login_required
# Semua view di bawah mengembalikan JSON untuk dipakai AJAX.

# Tambah ulasan baru ke sebuah resep (dipanggil lewat AJAX)
@login_required(login_url='main:login')
def add_review(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        images = request.FILES.getlist('images')

        # Rating wajib diisi, komentar dan foto boleh kosong
        if not rating:
            return JsonResponse({'success': False, 'error': 'Rating wajib diisi!'}, status=400)

        review = Review.objects.create(
            recipe=recipe,
            user=request.user,
            rating=int(rating),
            comment=comment
        )

        # Maksimal 3 foto per ulasan
        for img in images[:3]:
            ReviewImage.objects.create(review=review, image=img)

        # Kirim potongan HTML ulasan baru supaya JS bisa langsung menampilkannya
        html = render_to_string('reviews/_review_item.html', {'review': review}, request=request)
        return JsonResponse({'success': True, 'html': html})

    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


# Edit ulasan milik user yang sedang login
@login_required(login_url='main:login')
def edit_review(request, review_id):
    # user=request.user supaya user tidak bisa mengedit ulasan orang lain
    review = get_object_or_404(Review, pk=review_id, user=request.user)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if rating:
            review.rating = int(rating)
        review.comment = comment
        review.is_edited = True  # supaya label "(edited)" muncul
        review.save()

        # Foto baru ditambahkan ke foto lama, total tetap maksimal 3
        images = request.FILES.getlist('images')
        if images:
            current_count = review.images.count()
            allowed_slots = 3 - current_count
            for img in images[:allowed_slots]:
                ReviewImage.objects.create(review=review, image=img)

        # Kirim HTML ulasan yang sudah diperbarui untuk menggantikan kartu lama di halaman
        html = render_to_string('reviews/_review_item.html', {'review': review}, request=request)
        return JsonResponse({'success': True, 'html': html})

    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


# Hapus ulasan milik user yang sedang login
@login_required(login_url='main:login')
def delete_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id, user=request.user)

    # Hanya boleh lewat POST supaya tidak terhapus hanya karena membuka sebuah link
    if request.method == 'POST':
        review.delete()
        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)