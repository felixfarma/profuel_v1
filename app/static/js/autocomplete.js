document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('food-search');
    const resultsDiv = document.getElementById('results');

    searchInput.addEventListener('input', function () {
        const query = this.value.trim();

        if (query.length < 2) {
            resultsDiv.innerHTML = '';
            return;
        }

        fetch(`/search?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                resultsDiv.innerHTML = '';

                if (data.length === 0) {
                    resultsDiv.innerHTML = '<div>No se encontraron resultados.</div>';
                    return;
                }

                data.forEach(item => {
                    const div = document.createElement('div');
                    div.classList.add('autocomplete-item');
                    div.textContent = `${item.name} — ${item.kcal} kcal`;

                    div.addEventListener('click', () => {
                        document.getElementById('food-name').value = item.name;
                        document.getElementById('protein').value = item.protein;
                        document.getElementById('carbs').value = item.carbs;
                        document.getElementById('fat').value = item.fat;
                        document.getElementById('kcal').value = item.kcal;
                        resultsDiv.innerHTML = '';
                    });

                    resultsDiv.appendChild(div);
                });
            })
            .catch(error => {
                console.error('Error en la búsqueda:', error);
                resultsDiv.innerHTML = '<div>Error al buscar alimentos.</div>';
            });
    });
});
