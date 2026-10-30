// Pantry Tracker: pilih bahan, dialog edit/hapus, dan toast.
document.addEventListener("DOMContentLoaded", function () {
    // ---------- Pilih bahan untuk "Cari Resep dari Stok" ----------
    const selectAll = document.getElementById("select-all");
    const countBadge = document.getElementById("selected-count");
    const itemChecks = Array.from(document.querySelectorAll(".item-check"));
    const selectable = itemChecks.filter(function (box) { return !box.disabled; });

    function updateSelection() {
        const checked = selectable.filter(function (box) { return box.checked; }).length;

        if (countBadge) {
            countBadge.textContent = checked;
            countBadge.hidden = checked === 0;
        }

        if (selectAll) {
            selectAll.checked = selectable.length > 0 && checked === selectable.length;
            selectAll.indeterminate = checked > 0 && checked < selectable.length;
        }
    }

    if (selectAll) {
        selectAll.addEventListener("change", function () {
            selectable.forEach(function (box) { box.checked = selectAll.checked; });
            updateSelection();
        });
    }

    itemChecks.forEach(function (box) {
        box.addEventListener("change", updateSelection);
    });

    // Browser bisa mengembalikan centang lama saat tombol Back ditekan.
    updateSelection();

    // ---------- Urutkan: kirim form otomatis saat pilihan diganti ----------
    const sortSelect = document.getElementById("sort-select");

    if (sortSelect) {
        sortSelect.addEventListener("change", function () {
            sortSelect.form.submit();
        });
    }

    // ---------- Dialog Edit ----------
    const editDialog = document.getElementById("edit-dialog");
    const editForm = document.getElementById("edit-form");

    document.querySelectorAll(".js-edit").forEach(function (button) {
        button.addEventListener("click", function () {
            const data = button.dataset;

            editForm.action = data.url;
            editForm.elements["edit-name"].value = data.name;
            editForm.elements["edit-category"].value = data.category;
            editForm.elements["edit-quantity"].value = data.quantity;
            editForm.elements["edit-unit"].value = data.unit;
            editForm.elements["edit-storage"].value = data.storage;
            editForm.elements["edit-expiry_date"].value = data.expiry;
            editForm.elements["edit-recipe_name"].value = data.recipeName;

            editDialog.showModal();
        });
    });

    // ---------- Dialog Hapus ----------
    const deleteDialog = document.getElementById("delete-dialog");
    const deleteForm = document.getElementById("delete-form");
    const deleteName = document.getElementById("delete-name");

    document.querySelectorAll(".js-delete").forEach(function (button) {
        button.addEventListener("click", function () {
            deleteForm.action = button.dataset.url;
            deleteName.textContent = button.dataset.name;
            deleteDialog.showModal();
        });
    });

    // ---------- Tutup dialog (tombol Batal & klik di luar kotak) ----------
    [editDialog, deleteDialog].forEach(function (dialog) {
        dialog.querySelectorAll(".js-close").forEach(function (button) {
            button.addEventListener("click", function () { dialog.close(); });
        });

        dialog.addEventListener("click", function (event) {
            // Tutup hanya jika klik jatuh di luar kotak dialog (area backdrop)
            const box = dialog.getBoundingClientRect();
            const outside =
                event.clientX < box.left || event.clientX > box.right ||
                event.clientY < box.top || event.clientY > box.bottom;

            if (outside) {
                dialog.close();
            }
        });
    });

    // ---------- Form AJAX: validasi tanpa memuat ulang halaman ----------
    // Form dengan atribut data-ajax-form dikirim lewat fetch(). Kalau server menolak
    // (status 400), pesan error tampil di bawah kolom yang bermasalah dan isian tetap
    // utuh. Kalau berhasil, halaman dimuat ulang agar daftar bahan dan summary ikut
    // diperbarui, dan toast dari Django messages tampil seperti biasa.
    function clearErrors(form, name) {
        form.querySelectorAll("[data-ajax-error]").forEach(function (error) {
            if (!name || error.dataset.field === name) {
                error.remove();
            }
        });
    }

    function showError(form, name, message) {
        const control = form.elements[name];
        // Pilihan radio (mis. storage) berupa daftar elemen, ambil yang pertama
        const input = control && !control.tagName ? control[0] : control;
        const holder = input ? input.closest(".pantry-field") : null;

        const error = document.createElement("p");
        error.className = "pantry-error";
        error.setAttribute("role", "alert");
        error.dataset.ajaxError = "";
        error.dataset.field = name;
        error.textContent = message;

        if (holder) {
            holder.appendChild(error);
        } else {
            // Error umum (bukan milik satu kolom) tampil di bagian atas form
            form.prepend(error);
        }
    }

    document.querySelectorAll("form[data-ajax-form]").forEach(function (form) {
        // Error sebuah kolom hilang begitu kolom itu diubah lagi
        form.addEventListener("input", function (event) {
            clearErrors(form, event.target.name);
        });

        form.addEventListener("submit", function (event) {
            event.preventDefault();
            clearErrors(form);

            const submitButton = form.querySelector("button[type=submit]");
            if (submitButton) {
                submitButton.disabled = true;  // cegah klik ganda
            }

            fetch(form.action, {
                method: "POST",
                body: new FormData(form),  // sudah membawa csrfmiddlewaretoken
                headers: { "X-Requested-With": "XMLHttpRequest" },
                credentials: "same-origin",
            })
                .then(function (response) {
                    // Sesi habis: Django mengarahkan ke halaman login, ikuti saja
                    if (response.redirected) {
                        window.location.assign(response.url);
                        return null;
                    }
                    return response.json();
                })
                .then(function (data) {
                    if (!data) {
                        return;
                    }

                    if (data.ok) {
                        window.location.assign(data.redirect);
                        return;
                    }

                    Object.keys(data.errors).forEach(function (name) {
                        data.errors[name].forEach(function (message) {
                            showError(form, name, message);
                        });
                    });

                    if (submitButton) {
                        submitButton.disabled = false;
                    }

                    // Fokus ke kolom pertama yang bermasalah
                    const firstError = form.querySelector("[data-ajax-error]");
                    const holder = firstError && firstError.closest(".pantry-field");
                    const field = holder && holder.querySelector("input, select");
                    if (field) {
                        field.focus();
                    }
                })
                .catch(function () {
                    showError(form, "__all__", "Something went wrong. Please try again.");
                    if (submitButton) {
                        submitButton.disabled = false;
                    }
                });
        });
    });
});
