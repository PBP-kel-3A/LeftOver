// Smart Shopping List: tambah, centang "Sudah Dibeli", hapus, tab filter,
// dan pindah ke Pantry. Semua lewat AJAX tanpa reload halaman.
document.addEventListener("DOMContentLoaded", function () {
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;
    const list = document.getElementById("shop-list");
    const emptyText = document.getElementById("shop-empty");
    const addForm = document.getElementById("add-form");
    const transferBtn = document.getElementById("transfer-btn");
    const tabs = Array.from(document.querySelectorAll(".shop-tab"));
    const toast = document.getElementById("shop-toast");

    let activeFilter = "all";
    let toastTimer = null;

    // ---------- Helper ----------
    function post(url, body) {
        return fetch(url, {
            method: "POST",
            headers: { "X-CSRFToken": csrfToken },
            body: body,
        }).then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok || !data.success) {
                    throw new Error(data.error || "Terjadi kesalahan, coba lagi.");
                }
                return data;
            });
        });
    }

    // URL di template memakai id 0 sebagai placeholder
    function itemUrl(template, id) {
        return template.replace("/0/", "/" + id + "/");
    }

    function showToast(message, isError) {
        toast.textContent = message;
        toast.classList.toggle("is-error", Boolean(isError));
        toast.hidden = false;
        clearTimeout(toastTimer);
        toastTimer = setTimeout(function () { toast.hidden = true; }, 3000);
    }

    function items() {
        return Array.from(list.querySelectorAll(".shop-item"));
    }

    function matchesFilter(item) {
        const purchased = item.classList.contains("is-purchased");
        if (activeFilter === "pending") return !purchased;
        if (activeFilter === "purchased") return purchased;
        return true;
    }

    // Hitung ulang angka di tab, tampilkan item sesuai tab, dan status tombol
    function refresh() {
        const all = items();
        const purchased = all.filter(function (item) {
            return item.classList.contains("is-purchased");
        }).length;

        document.querySelector('[data-count="all"]').textContent = all.length;
        document.querySelector('[data-count="pending"]').textContent = all.length - purchased;
        document.querySelector('[data-count="purchased"]').textContent = purchased;

        let visible = 0;
        all.forEach(function (item) {
            const show = matchesFilter(item);
            item.hidden = !show;
            if (show) visible++;
        });

        emptyText.hidden = visible > 0;
        transferBtn.disabled = purchased === 0;
    }

    function removeItem(item) {
        item.classList.add("is-leaving");
        setTimeout(function () {
            item.remove();
            refresh();
        }, 250);
    }

    // ---------- Tambah barang ----------
    addForm.addEventListener("submit", function (event) {
        event.preventDefault();
        const nameInput = addForm.querySelector("[name=name]");

        if (!nameInput.value.trim()) {
            nameInput.classList.add("is-invalid");
            nameInput.focus();
            showToast("Nama bahan wajib diisi.", true);
            return;
        }
        nameInput.classList.remove("is-invalid");

        const submitBtn = addForm.querySelector("button[type=submit]");
        submitBtn.disabled = true;

        post(addForm.action, new FormData(addForm))
            .then(function (data) {
                list.insertAdjacentHTML("afterbegin", data.html);
                addForm.reset();
                nameInput.focus();
                refresh();
                showToast(data.name + " ditambahkan ke daftar belanja.");
            })
            .catch(function (error) { showToast(error.message, true); })
            .finally(function () { submitBtn.disabled = false; });
    });

    // ---------- Centang "Sudah Dibeli" ----------
    list.addEventListener("change", function (event) {
        if (!event.target.classList.contains("shop-checkbox")) return;

        const checkbox = event.target;
        const item = checkbox.closest(".shop-item");

        // Langsung coret di tampilan, baru kirim ke server
        item.classList.toggle("is-purchased", checkbox.checked);
        refresh();

        post(itemUrl(list.dataset.toggleUrl, item.dataset.id))
            .then(function (data) {
                // Samakan dengan data di server
                checkbox.checked = data.is_purchased;
                item.classList.toggle("is-purchased", data.is_purchased);
                refresh();
            })
            .catch(function (error) {
                // Gagal: kembalikan seperti semula
                checkbox.checked = !checkbox.checked;
                item.classList.toggle("is-purchased", checkbox.checked);
                refresh();
                showToast(error.message, true);
            });
    });

    // ---------- Hapus barang ----------
    list.addEventListener("click", function (event) {
        const deleteBtn = event.target.closest(".shop-delete");
        if (!deleteBtn) return;

        const item = deleteBtn.closest(".shop-item");
        deleteBtn.disabled = true;

        post(itemUrl(list.dataset.deleteUrl, item.dataset.id))
            .then(function (data) {
                removeItem(item);
                showToast(data.name + " dihapus dari daftar belanja.");
            })
            .catch(function (error) {
                deleteBtn.disabled = false;
                showToast(error.message, true);
            });
    });

    // ---------- Tab filter ----------
    tabs.forEach(function (tab) {
        tab.addEventListener("click", function () {
            activeFilter = tab.dataset.filter;
            tabs.forEach(function (other) {
                const active = other === tab;
                other.classList.toggle("is-active", active);
                other.setAttribute("aria-selected", active);
            });
            refresh();
        });
    });

    // ---------- Pindahkan ke Pantry ----------
    transferBtn.addEventListener("click", function () {
        transferBtn.disabled = true;

        post(transferBtn.dataset.url)
            .then(function (data) {
                data.moved_ids.forEach(function (id) {
                    const item = list.querySelector('.shop-item[data-id="' + id + '"]');
                    if (item) removeItem(item);
                });
                showToast(data.count + " bahan dipindahkan ke stok dapur. Cek tanggal kedaluwarsanya di Pantry ya!");
            })
            .catch(function (error) {
                refresh();
                showToast(error.message, true);
            });
    });

    // Browser bisa mengembalikan centang lama saat tombol Back ditekan,
    // jadi samakan lagi dengan status dari server (class is-purchased).
    items().forEach(function (item) {
        item.querySelector(".shop-checkbox").checked = item.classList.contains("is-purchased");
    });
    refresh();
});
