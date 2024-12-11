export function setupDeleteModal(modalId, confirmBtnId, deleteCallback, getModalTextCallback, txs = null) {
    let deleteEvent = null;

    document.addEventListener("click", function (e) {
        if (e.target.classList.contains("delete-btn")) {
            deleteEvent = e;

            const modalText = getModalTextCallback(e.target);

            const modalBody = document.querySelector(`#${modalId} .modal-body`);
            if (modalBody && modalText) {
                    modalBody.textContent = modalText;
            }

            const modal = new bootstrap.Modal(document.getElementById(modalId));
            modal.show();
        }
    });

    document.getElementById(confirmBtnId).addEventListener("click", function () {
        if (deleteEvent) {
            deleteCallback(deleteEvent.target, txs);
            deleteEvent = null;
        }

        const modal = bootstrap.Modal.getInstance(document.getElementById(modalId));
        modal.hide();
    });
}

export function showErrorToast(errorMessage) {
    const toastContainer = document.getElementById("toast-container");
    const toast = document.createElement("div");

    toast.className = "toast align-items-center text-bg-danger border-0 show";
    toast.role = "alert";
    toast.ariaLive = "assertive";
    toast.ariaAtomic = "true";

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${errorMessage}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 5000);
}
