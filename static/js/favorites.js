
// ==========================================
// LEFTOVER — FAVORITES INTERACTIONS
// ==========================================

document.addEventListener("DOMContentLoaded", () => {

    const modal = document.getElementById("edit-note-modal");
    const form = document.getElementById("edit-note-form");

    if (!modal || !form) return;

    const input = document.getElementById("modal-personal-note");
    const recipeName = document.getElementById("modal-recipe-name");
    const errorText = document.getElementById("note-error");
    const saveBtn = document.getElementById("save-note-btn");

    let activeNoteId = null;
    let activeDisplayId = null;
    let isSaving = false;
    let triggerButton = null;

    // ---------- DELETE CONFIRMATION ----------

    document.querySelectorAll(".fav-remove-form").forEach((removeForm) => {
        removeForm.addEventListener("submit", (event) => {

            const message =
                removeForm.dataset.confirm ||
                "Remove this recipe from your favorites?";

            if (!window.confirm(message)) {
                event.preventDefault();
            }

        });
    });

    // ---------- CLOSE MODAL ----------

    function closeModal() {

        if (isSaving) return;

        modal.hidden = true;
        document.body.style.overflow = "";

        form.reset();

        activeNoteId = null;
        activeDisplayId = null;

        if (triggerButton) {
            triggerButton.focus();
        }
    }

    // ---------- OPEN MODAL ----------

    document.querySelectorAll(".fav-edit-btn").forEach((button) => {

        button.addEventListener("click", () => {

            triggerButton = button;

            activeNoteId = button.dataset.noteId;
            activeDisplayId = button.dataset.displayId;

            const storedNote = document.getElementById(activeNoteId);

            if (!storedNote) return;

            // Load the existing note from the selected card.
            input.value = storedNote.value;

            // Set the update URL for the selected favorite.
            form.action = button.dataset.updateUrl;

            recipeName.textContent = button.dataset.recipeName;

            // Clear previous errors.
            errorText.hidden = true;
            errorText.textContent = "";

            // Display the modal.
            modal.hidden = false;
            document.body.style.overflow = "hidden";

            input.focus();
        });

    });

    // ---------- MODAL CONTROLS ----------

    document.getElementById("close-note-modal")
        .addEventListener("click", closeModal);

    document.getElementById("cancel-note-modal")
        .addEventListener("click", closeModal);

    // Close when clicking outside the modal panel.
    modal.addEventListener("click", (event) => {
        if (event.target === modal) {
            closeModal();
        }
    });

    // Close using the Escape key.
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !modal.hidden) {
            closeModal();
        }
    });

    // ---------- UPDATE PERSONAL NOTES ----------

    form.addEventListener("submit", async (event) => {

        // Prevent the default page reload.
        event.preventDefault();

        if (isSaving) return;

        isSaving = true;
        saveBtn.disabled = true;
        saveBtn.textContent = "Saving...";

        errorText.hidden = true;
        errorText.textContent = "";

        try {

            // Include personal_note and csrfmiddlewaretoken.
            const formData = new FormData(form);

            const response = await fetch(form.action, {
                method: "POST",
                body: formData,
                credentials: "same-origin",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            });

            // Redirect to login if the session has expired.
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }

            const data = await response.json();

            // Handle unsuccessful responses.
            if (!response.ok || !data.success) {

                const details = data.errors
                    ? Object.values(data.errors)
                        .flat()
                        .map((entry) => entry.message || String(entry))
                        .join(" ")
                    : "";

                throw new Error(
                    details ||
                    data.message ||
                    "Failed to save your notes. Please try again."
                );
            }

            // Get the selected card's note elements.
            const storedNote = document.getElementById(activeNoteId);
            const displayedNote = document.getElementById(activeDisplayId);

            // Update the stored note.
            if (storedNote) {
                storedNote.value = data.personal_note;
            }

            // Update the visible note without reloading.
            if (displayedNote) {
                displayedNote.textContent = data.personal_note.trim()
                    ? data.personal_note
                    : "No notes yet. Click Edit to add one.";
            }

            isSaving = false;
            closeModal();

        } catch (error) {

            errorText.textContent =
                error.message || "Something went wrong. Please try again.";

            errorText.hidden = false;

        } finally {

            isSaving = false;
            saveBtn.disabled = false;
            saveBtn.textContent = "Save Notes";

        }
    });

});
