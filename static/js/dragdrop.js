document.addEventListener("DOMContentLoaded", function () {
    let draggedElement = null;

    // Zorg ervoor dat alle technieken absoluut gepositioneerd zijn
    document.querySelectorAll(".technique").forEach(item => {
        item.style.position = "absolute"; // Zorgt ervoor dat elementen vrij kunnen bewegen

        // Stel de positie in op basis van opgeslagen waarden
        const id = item.id;
        setPosition(id); // Deze functie zal de positie herstellen bij het laden van de pagina

        item.addEventListener("dragstart", function (event) {
            draggedElement = event.target;
            event.dataTransfer.setData("text/plain", null); // Nodig voor sommige browsers
        });

        item.addEventListener("dragend", function (event) {
            // Zet de nieuwe positie vast
            draggedElement.style.left = event.pageX - draggedElement.offsetWidth / 2 + "px";
            draggedElement.style.top = event.pageY - draggedElement.offsetHeight / 2 + "px";
            savePosition(draggedElement.id); // Sla de nieuwe positie op
        });
    });

    // Functie om te zorgen dat slepen toegestaan is
    document.addEventListener("dragover", function (event) {
        event.preventDefault(); // Nodig om slepen toe te staan
    });

    // Functie om te zorgen dat het vlakje op de juiste plaats wordt gedropt
    document.addEventListener("drop", function (event) {
        event.preventDefault(); // Zorgt ervoor dat de drop werkt
        if (draggedElement) {
            draggedElement.style.left = event.pageX - draggedElement.offsetWidth / 2 + "px";
            draggedElement.style.top = event.pageY - draggedElement.offsetHeight / 2 + "px";
            savePosition(draggedElement.id); // Sla de nieuwe positie op
        }
    });
});

// Functie om de positie van het vlakje op te slaan
function savePosition(id) {
    const element = document.getElementById(id);
    const position = element.getBoundingClientRect();  // Verkrijg de huidige positie
    localStorage.setItem(id + "_position", JSON.stringify({ top: position.top, left: position.left }));
}

// Functie om de positie van het vlakje in te stellen
function setPosition(id) {
    const position = JSON.parse(localStorage.getItem(id + "_position"));
    if (position) {
        const element = document.getElementById(id);
        element.style.position = "absolute";  // Zorg ervoor dat het absoluut wordt gepositioneerd
        element.style.top = position.top + "px";
        element.style.left = position.left + "px";
    }
}

// Functie om draggable uit te schakelen
function disableDrag(id) {
    const element = document.getElementById(id);
    element.setAttribute("draggable", "false");
    savePosition(id);  // Sla de positie op voordat je draggable uitschakelt
}
