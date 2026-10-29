from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.loader import render_to_string
from recipes.models import Recipe
from .models import Review, ReviewImage
import cloudinary.uploader 

# Semua tindakan di cakupan "Reviews" hanya bisa dilakukan akun yang sudah login --> @login_required
# Semua view di bawah mengembalikan JSON untuk dipakai AJAX.

# Konstanta batas upload gambar
MAX_IMAGE_SIZE_BYTES = 2 * 1024 * 1024  # Maksimal 2MB per foto
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}

def _valid_rating(value):
    # Mengembalikan rating sebagai integer 1-5, atau None kalau tidak valid
    try:
        rating = int(value)
    except (TypeError, ValueError):
        return None
    return rating if 1 <= rating <= 5 else None

def _validate_image(file_obj):
    # Validasi tipe MIME dan batas ukuran file di sisi server
    content_type = getattr(file_obj, 'content_type', '')
    if content_type not in ALLOWED_IMAGE_TYPES:
        return 'Only JPG, PNG, and WebP images are allowed!'
    if file_obj.size > MAX_IMAGE_SIZE_BYTES:
        return 'Each photo must not exceed 2MB in size!'
    return None

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

        # Maksimal 3 foto per ulasan
        images = request.FILES.getlist('images')
        if len(images) > 3:
            return JsonResponse({'success': False, 'error': 'You can only upload up to 3 photos!'}, status=400)

        # Validasi setiap file foto sebelum disimpan
        for img in images:
            err = _validate_image(img)
            if err:
                return JsonResponse({'success': False, 'error': err}, status=400)

        review = Review.objects.create(
            recipe=recipe,
            user=request.user,
            rating=int(rating),
            comment=comment
        )

        # loop foto 3 kali
        for img in images[:3]:
            try:
                # Upload ke Cloudinary
                upload_result = cloudinary.uploader.upload(img)
                image_url = upload_result.get('secure_url')
                
                # Simpan URL Cloudinary ke database
                ReviewImage.objects.create(review=review, image=image_url)
            except Exception as e:
                print(f"Cloudinary upload error: {e}")
                continue

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

        # Foto baru ditambahkan ke foto lama, total tetap maksimal 3
        images = request.FILES.getlist('images')
        current_count = review.images.count()

        if images:
            allowed_slots = 3 - current_count
            if allowed_slots <= 0:
                return JsonResponse({'success': False, 'error': 'This review already has 3 photos. Delete existing photos first to add new ones.'}, status=400)
            if len(images) > allowed_slots:
                return JsonResponse({'success': False, 'error': f'You can only add {allowed_slots} more photo(s).'}, status=400)

            # Validasi file foto baru
            for img in images:
                err = _validate_image(img)
                if err:
                    return JsonResponse({'success': False, 'error': err}, status=400)

            for img in images:
                try:
                    # Upload ke Cloudinary dan ambil secure_url-nya
                    upload_result = cloudinary.uploader.upload(img)
                    image_url = upload_result.get('secure_url')
                    
                    # Simpan URL Cloudinary ke model ReviewImage
                    ReviewImage.objects.create(review=review, image=image_url)
                except Exception as e:
                    print(f"Cloudinary upload error: {e}")
                    continue

        review.comment = request.POST.get('comment', '').strip()
        review.is_edited = True  # supaya label "(edited)" muncul
        review.save()

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