console.log("[script.js] loaded");

window.resizeWordTextboxes = function (words) {
    const textboxes = document.querySelectorAll(".word");

    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");

    for (let i = 0; i < words.length; i++) {
        const container = textboxes[i];
        const input = container.querySelector("input")
        const word = words[i];
        const style = getComputedStyle(input);

        ctx.font = [
            style.fontStyle,
            style.fontWeight,
            style.fontSize,
            style.fontFamily
        ].join(" ");

        const textWidth = ctx.measureText(word).width;
        const width = Math.ceil(textWidth);

        container.style.minWidth = `min(calc(${width}px + ${style.paddingLeft} + ${style.paddingRight}), 100%)`;
        console.log(container.style.minWidth);
    }
};

window.test = function (words) {
    alert(words);
};
