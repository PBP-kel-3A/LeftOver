from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.loader import render_to_string
from recipes.models import Recipe
from .models import Review, ReviewImage
import cloudinary.uploader 

# Semua tindakan di cakupan "Reviews" hanya bisa dilakukan akun yang sudah login --> @login_required
# Semua view di bawah mengembalikan JSON untuk dipakai AJAX.

def _valid_rating(value):
    # membatasi nilai bintang hanya di rentang 1 sampai 5
    try:
        rating = int(value)
    except (TypeError, ValueError):
        return None
    return rating if 1 <= rating <= 5 else None

# Tambah ulasan baru ke sebuah resep (dipanggil lewat AJAX)
@login_required(login_url='main:login')
def add_review(request, recipe_id):
    #  ngambil resep target
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    # di sini ekstraksi form POST
    if request.method == 'POST':
        # Untuk menjaga 1 user hanya bisa me-review satu kali
        if Review.objects.filter(recipe=recipe, user=request.user).exists():
            return JsonResponse({'success': False, 'error': 'You have already reviewed this recipe!'}, status=400)

        # Rating wajib diisi, komentar dan foto boleh kosong
        rating = _valid_rating(request.POST.get('rating'))
        if rating is None:
            return JsonResponse({'success': False, 'error': 'Rating must be between 1 and 5 stars!'}, status=400)

        comment = request.POST.get('comment', '').strip()

        review = Review.objects.create(
            recipe=recipe,
            user=request.user,
            rating=int(rating),
            comment=comment
        )

        # Maksimal 3 foto per ulasan
        images = request.FILES.getlist('images')
        # Loop foto 3 kali
        for img in images[:3]:
            try:
                # Upload ke Cloudinary
                upload_result = cloudinary.uploader.upload(img)
                image_url = upload_result.get('secure_url')
                # Simpan URL Cloudinary ke database
                ReviewImage.objects.create(review=review, image=image_url)
            except Exception as e:
                print(f"Cloudinary upload error: {e}")
                continue  # Lewati foto yang gagal, proses ulasan tetap lanjut tersimpan

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
        rating_input = request.POST.get('rating')

        if rating_input:
            valid_rating = _valid_rating(rating_input)
            if valid_rating is None:
                return JsonResponse({'success': False, 'error': 'Rating must be between 1 and 5 stars!'}, status=400)
            review.rating = valid_rating

        review.comment = request.POST.get('comment', '').strip()
        review.is_edited = True  # supaya label "(edited)" muncul
        review.save()

        # Foto baru ditambahkan ke foto lama, total tetap maksimal 3
        images = request.FILES.getlist('images')
        if images:
            current_count = review.images.count()
            allowed_slots = max(0, 3 - current_count) # menghitung sisa slot yang tersedia -> mencegah negatif
            
            for img in images[:allowed_slots]:
                try:
                    # Upload ke Cloudinary dan ambil secure_url-nya
                    upload_result = cloudinary.uploader.upload(img)
                    image_url = upload_result.get('secure_url')
                    # Simpan URL Cloudinary ke model ReviewImage
                    ReviewImage.objects.create(review=review, image=image_url)
                except Exception as e:
                    print(f"Cloudinary upload error: {e}")
                    continue  # Lewati foto yang gagal

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
        # Hapus foto-foto terkait dari Cloudinary-nya
        for img in review.images.all():
            if img.image:
                try:
                    # format URL: https://res.cloudinary.com/.../image/upload/v12345678/folder_name/filename.jpg
                    url_parts = str(img.image).split('/')
                    file_with_ext = url_parts[-1]
                    file_name, _ = file_with_ext.rsplit('.', 1)
                    
                    if 'review_images' in str(img.image):
                        public_id = f"review_images/{file_name}"
                    else:
                        public_id = file_name
                    # delete file fisik yang ada di Cloudinary juga
                    cloudinary.uploader.destroy(public_id)
                except Exception as e:
                    print(f"Cloudinary deletion error: {e}")

        # Hapus data ulasan dari database (ReviewImage akan ikut terhapus otomatis karena CASCADE)
        review.delete()
        return JsonResponse({'success': True})
        
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)