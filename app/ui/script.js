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
    }
};

window.test = function (words) {
    alert(words);
};

function enableWordNavigation() {
    if (window.wordNavigationEnabled) {
        return;
    }

    window.wordNavigationEnabled = true;

    document.addEventListener("keydown", (event) => {
        const input = event.target.closest(
            ".text-input input"
        );

        if (!input) {
            return;
        }

        const container = input.closest(".phrase-en");

        if (!container) {
            return;
        }

        const inputs = Array.from(
            container.querySelectorAll(
                ".text-input input"
            )
        );

        const index = inputs.indexOf(input);

        if (index === -1) {
            return;
        }

        // Space → next textbox
        if (event.key === " ") {
            event.preventDefault();

            if (index < inputs.length - 1) {
                const next = inputs[index + 1];

                next.focus();
                next.select();
            }

            return;
        }

        // Backspace on empty textbox → previous textbox
        if (
            event.key === "Backspace" &&
            input.selectionStart === 0 &&
            input.selectionEnd === 0 &&
            index > 0
        ) {
            event.preventDefault();

            const previous = inputs[index - 1];

            previous.focus();

            // Put caret at the end of the previous word.
            previous.setSelectionRange(
                previous.value.length,
                previous.value.length
            );
        }

        // Left Arrow
        if (
            event.key === "ArrowLeft" &&
            input.selectionStart === 0 &&
            input.selectionEnd === 0 &&
            index > 0
        ) {
            event.preventDefault();

            const previous = inputs[index - 1];

            previous.focus();

            previous.setSelectionRange(
                previous.value.length,
                previous.value.length
            );

            return;
        }

        // Right Arrow
        if (
            event.key === "ArrowRight" &&
            input.selectionStart === input.value.length &&
            input.selectionEnd === input.value.length &&
            index < inputs.length - 1
        ) {
            event.preventDefault();

            const next = inputs[index + 1];

            next.focus();

            next.setSelectionRange(0, 0);

            return;
        }
    });
};

enableWordNavigation()