document.addEventListener("DOMContentLoaded", function () {
    const toasts = document.querySelectorAll(".toast");

    toasts.forEach((toast) => {
        // Tunggu 3 detik sebelum menghilangkan toast
        setTimeout(() => {
            toast.classList.add("toast-hide");

            // Hapus elemen setelah animasi selesai
            setTimeout(() => {
                toast.remove();

                const container = document.querySelector(".toast-container");

                if (container && container.children.length === 0) {
                    container.remove();
                }
            }, 400);

        }, 3000);
    });
});