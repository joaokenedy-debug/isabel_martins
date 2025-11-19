const banners = [
    {
        titulo: "RADAR DA LIDERANÇA® ",
        texto1: "Clareza para crescer. Direção para evoluir. Ação para performar.",
        texto2: "Descubra exatamente o que está travando sua liderança — e o que vai acelerar seus resultados imediatamente.",
        imagem: "static/fotos/isabel.png",
        reverso: false
    },
    {
        titulo: "RADAR DA LIDERANÇA® ",
        texto1: "Clareza para crescer. Direção para evoluir. Ação para performar.",
        texto2: "O Radar da Liderança® é a ferramenta que líderes escolhem quando querem deixar de “tentar de tudo um pouco” e começar a evoluir com foco, estratégia e métricas reais.",
        imagem: "static/fotos/isabel.png",
        reverso: true
    }
];

let index = 0;
const banner = document.getElementById("banner");
const bannerText = document.getElementById("banner-text");
const bannerImg = document.getElementById("banner-img").querySelector("img");

function trocarBanner() {
    index = (index + 1) % banners.length;
    const b = banners[index];

    banner.classList.toggle("reverse", b.reverso);
    bannerText.querySelector("h2").innerHTML = b.titulo;
    bannerText.getElementById("subtitulo").innerHTML = b.texto1;
    bannerText.getElementById("texto2").innerHTML = b.texto2;
    bannerImg.src = b.imagem;
}

// Troca automática a cada 15 segundos
setInterval(trocarBanner, 15000);

// Troca manual pelo botão
document.getElementById("nextBanner").addEventListener("click", trocarBanner);