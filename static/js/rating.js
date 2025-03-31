// static/js/rating.js
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.video-rating').forEach(function(videoRating) {
        const ratingBands = videoRating.querySelectorAll('.rating-band');
        const voteButton = videoRating.parentElement.querySelector('.vote-button');
        const averageScore = videoRating.parentElement.querySelector('.average-rating');
        const totalVotes = videoRating.parentElement.querySelector('.total-votes');
        const videoId = videoRating.getAttribute('data-video-id');
        const hasVoted = videoRating.getAttribute('data-has-voted') === 'true'; // Check initiële stemstatus

        let rating = 0;

        // Als al gestemd, disable banden interactie
        if (!hasVoted) {
            ratingBands.forEach(function(band) {
                band.addEventListener('click', function() {
                    const blackBelt = band.getAttribute('data-black');
                    const whiteBelt = band.getAttribute('data-white');
                    rating = parseInt(band.getAttribute('data-value'));

                    ratingBands.forEach(function(b) {
                        b.querySelector('.rating-image').src = whiteBelt;
                    });

                    ratingBands.forEach(function(b) {
                        if (parseInt(b.getAttribute('data-value')) <= rating) {
                            b.querySelector('.rating-image').src = blackBelt;
                        }
                    });
                });
            });
        }

        // Bepaal de juiste fetch-URL op basis van de pagina
        let voteUrl;
        if (window.location.pathname === '/exercises') {
            voteUrl = '/vote/exercises'; // Voor de exercises-pagina
        } else {
            const technique = window.location.pathname.split('/').pop(); // Bijv. "O-goshi"
            voteUrl = `/vote/tachiwaza/${technique}`; // Voor tachiwaza-technieken
        }

        // Stemknop logica (alleen als niet gestemd)
        if (!hasVoted) {
            voteButton.addEventListener('click', function() {
                if (rating === 0) {
                    console.log('Geen rating geselecteerd');
                    return;
                }

                fetch(voteUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        video_id: videoId,
                        rating: rating
                    })
                })
                .then(response => {
                    if (!response.ok) throw new Error(`Serverfout: ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    averageScore.textContent = `${data.average_rating}`;
                    totalVotes.textContent = data.total_votes;
                    voteButton.disabled = true;
                    videoRating.setAttribute('data-has-voted', 'true'); // Update frontend status
                })
                .catch(error => {
                    console.error('Fout bij stemmen:', error);
                });
            });
        }
    });
});