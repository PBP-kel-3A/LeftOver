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
});
