# Artifact Tool authoring

Use this reference after the slide plan identifies source template slide numbers.

## Runtime setup

Resolve the bundled workspace dependencies and use the returned Node.js executable and Node.js package directory. Set `RUNTIME_NODE_MODULES` to the absolute package directory. Keep build files in a private task directory and the final PPTX in a separate output directory.

For custom `.mjs` authoring modules that use bare imports, link the runtime package directory as `node_modules` inside the private build directory before running the module. Do not install another copy of `@oai/artifact-tool`.

Create a starter deck with the selected source-slide order:

```bash
RUNTIME_NODE_MODULES=/absolute/path/to/node_modules \
/absolute/path/to/node scripts/create_starter_deck.mjs \
  --slides 1,3,5,7,11,13,20 \
  --output /absolute/path/to/build/starter.pptx
```

The script imports the full template, duplicates the selected slides, removes the original library slides, preserves the masters and layouts, and exports a clean deck. It refuses to overwrite an existing output.

## Inspect before editing

Use inspect anchors instead of guessing object indexes:

```js
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const presentation = await PresentationFile.importPptx(
  await FileBlob.load(starterPath),
);

const snapshot = await presentation.inspect({
  kind: "slide,textbox,shape,image,table,chart,notes,layout",
  maxChars: 20000,
});

process.stdout.write(snapshot.ndjson);
```

Resolve only IDs returned by the inspection:

```js
const slide = presentation.resolve(slideAnchorId);
const title = presentation.resolve(titleAnchorId);
title.text.replace(oldTitle, newTitle);
slide.speakerNotes.textFrame.setText(notesText);
slide.speakerNotes.setVisible(true);
```

For real placeholders, prefer the placeholder API:

```js
const title = slide.placeholders.getItem("title");
title.text = "Customer solution overview";
```

When replacing an imported image, preserve placement-affecting properties:

```js
const image = presentation.resolve(imageAnchorId);
const frame = image.frame;
const crop = image.crop;
const fit = image.fit;
const geometry = image.geometry;
const borderRadius = image.borderRadius;
const rotation = image.rotation;
const flipHorizontal = image.flipHorizontal;
const flipVertical = image.flipVertical;
const lockAspectRatio = image.lockAspectRatio;

image.replace({
  blob: replacementBytes,
  contentType: "image/png",
  alt: replacementAltText,
});
image.frame = frame;
image.crop = crop;
image.fit = fit;
image.geometry = geometry;
image.borderRadius = borderRadius;
image.rotation = rotation;
image.flipHorizontal = flipHorizontal;
image.flipVertical = flipVertical;
image.lockAspectRatio = lockAspectRatio;
```

## Export and review

Export the draft to a new path:

```js
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
```

Render changed slides before and after edits. Export layout JSON when placement matters:

```js
const preview = await slide.export({ format: "png", scale: 2 });
const layout = await slide.export({ format: "layout" });
```

Validate the candidate with `scripts/validate_byteplus_pptx.py`, render every slide, inspect the full deck visually, and re-import the final PPTX before delivery.
