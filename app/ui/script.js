console.log("[script.js] loaded");

window.updateTextboxes = function (words) {
    const textboxes = document.querySelectorAll(".word");
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");

    for (let i = 0; i < words.length; i++) {
        const container = textboxes[i];
        const input = container.querySelector("input")
        const target_word = words[i];

        // Measure the width of the input box according to the given word
        const style = getComputedStyle(input);
        ctx.font = [
            style.fontStyle,
            style.fontWeight,
            style.fontSize,
            style.fontFamily
        ].join(" ");

        const textWidth = ctx.measureText(target_word).width;
        const width = Math.ceil(textWidth);
        container.style.minWidth = `calc(${width}px + ${style.paddingLeft} + ${style.paddingRight})`;
        
        // Update the text color of the input according to the correctness of the input
        const COLOR_INCORRECT = "#e39696";
        const COLOR_CORRECT = "#47c7b8";
        const COLOR_PARTIALLY_CORRECT = "#4783c7";
        const COLOR_PARTIALLY_CORRECT_CASE = "#e4ba4d";
        
        input.oninput = (e)=> {
            const val = e.target.value;
            const partial_target = target_word.substring(0, val.length);
            let color = COLOR_INCORRECT;

            if (val == target_word) {
                color = COLOR_CORRECT;
            }

            else if (val.length > 0 && val == partial_target) {
                color = COLOR_PARTIALLY_CORRECT;
            }
            
            else if (val.length > 0 && partial_target.toLowerCase() == val.toLowerCase()) {
                color = COLOR_PARTIALLY_CORRECT_CASE;
            }

            input.style.color = color;
            input.style.borderColor = color;

            // Update the tip bubbles
            const tip_bubbles = document.querySelectorAll(".tip-bubble");
            const tip_dict = {
                [COLOR_INCORRECT]: tip_bubbles[0],
                [COLOR_PARTIALLY_CORRECT_CASE]: tip_bubbles[1],
                [COLOR_PARTIALLY_CORRECT]: tip_bubbles[2],
                [COLOR_CORRECT]: tip_bubbles[3],
            }
            for (let t of tip_bubbles) {
                t.style.borderWidth = "0px";
            }
            tip_dict[color].style.borderWidth = "4px";
            tip_dict[color].style.transform = "translateY(-12px)";
            
            if (tip_dict[color].timeout) {
                clearTimeout(tip_dict[color].timeout);
            }
            tip_dict[color].timeout = setTimeout(() => {
                tip_dict[color].style.transform = "translateY(0px)";
            }, 100);
        }
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