// Show loading spinner on form submit
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('analysis-form');
    const btn = document.getElementById('run-btn');
    const spinner = document.getElementById('spinner');

    if (form && btn && spinner) {
        form.addEventListener('submit', function() {
            btn.disabled = true;
            spinner.classList.remove('d-none');
            btn.classList.add('loading');
        });
    }
});
