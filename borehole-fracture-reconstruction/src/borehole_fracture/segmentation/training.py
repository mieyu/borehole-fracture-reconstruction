"""Group-aware dataset preparation and U-Net training with paired augmentation."""
from pathlib import Path
import json
import numpy as np
from ..io import read_image, read_mask


def train(dataset_manifest, output, epochs=100, batch_size=4, height=512, width=256, seed=42):
    import tensorflow as tf
    if min(epochs,batch_size,height,width) < 1 or height % 4 or width % 4:
        raise ValueError("Training dimensions must be multiples of four; all counts must be positive")
    tf.keras.utils.set_random_seed(seed)
    manifest = Path(dataset_manifest).resolve()
    samples = json.loads(manifest.read_text(encoding="utf-8"))["samples"]
    groups = sorted({str(s["group_id"]) for s in samples})
    if len(groups) < 2:
        raise ValueError("Training requires at least two independent source groups")
    rng = np.random.default_rng(seed)
    rng.shuffle(groups)
    validation_groups = set(groups[:max(1,int(np.ceil(len(groups)*.2)))])
    train_samples = [s for s in samples if str(s["group_id"]) not in validation_groups]
    val_samples = [s for s in samples if str(s["group_id"]) in validation_groups]
    for sample in samples:
        for key in ("image", "mask"):
            if not (manifest.parent/sample[key]).is_file():
                raise FileNotFoundError(manifest.parent/sample[key])

    def dataset(selected, augment=False):
        def generator():
            for sample in selected:
                image = read_image(manifest.parent/sample["image"])[...,::-1].copy()
                mask = read_mask(manifest.parent/sample["mask"])
                if image.shape[:2] != mask.shape:
                    raise ValueError("Training image and mask dimensions must match")
                yield image.astype(np.float32)/255,mask.astype(np.float32)[...,None]
        ds = tf.data.Dataset.from_generator(generator,output_signature=(
            tf.TensorSpec((None,None,3),tf.float32),tf.TensorSpec((None,None,1),tf.float32)))
        def prepare(image,mask):
            image = tf.image.resize_with_pad(image,height,width)
            mask = tf.image.resize_with_pad(mask,height,width,method="nearest")
            if augment:
                flip = tf.random.uniform(()) > .5
                image = tf.cond(flip,lambda:tf.image.flip_left_right(image),lambda:image)
                mask = tf.cond(flip,lambda:tf.image.flip_left_right(mask),lambda:mask)
                image = tf.clip_by_value(tf.image.random_brightness(image,.1),0,1)
            return image,mask
        if augment:
            ds = ds.shuffle(len(selected),seed=seed)
        return ds.map(prepare,num_parallel_calls=tf.data.AUTOTUNE).batch(batch_size).prefetch(tf.data.AUTOTUNE)

    layers = tf.keras.layers
    def block(tensor,filters):
        tensor = layers.Conv2D(filters,3,padding="same",activation="relu")(tensor)
        tensor = layers.Dropout(.1)(tensor)
        return layers.Conv2D(filters,3,padding="same",activation="relu")(tensor)
    inputs = layers.Input((height,width,3))
    c1 = block(inputs,16)
    c2 = block(layers.MaxPool2D()(c1),32)
    c3 = block(layers.MaxPool2D()(c2),64)
    c4 = block(layers.Concatenate()([layers.Conv2DTranspose(32,2,strides=2)(c3),c2]),32)
    c5 = block(layers.Concatenate()([layers.Conv2DTranspose(16,2,strides=2)(c4),c1]),16)
    model = tf.keras.Model(inputs,layers.Conv2D(1,1,activation="sigmoid")(c5))
    model.compile(optimizer="adam",loss="binary_crossentropy",metrics=[tf.keras.metrics.BinaryIoU(target_class_ids=[1])])
    output = Path(output);output.mkdir(parents=True,exist_ok=True)
    callbacks = [tf.keras.callbacks.ModelCheckpoint(str(output/"best.keras"),monitor="val_loss",save_best_only=True),
                 tf.keras.callbacks.EarlyStopping(monitor="val_loss",patience=15,restore_best_weights=True)]
    history = model.fit(dataset(train_samples,True),validation_data=dataset(val_samples),
                        epochs=epochs,callbacks=callbacks)
    model.save(output/"fracture_unet.keras")
    metadata = {"seed":seed,"train_groups":sorted(set(groups)-validation_groups),
                "validation_groups":sorted(validation_groups),"train_samples":len(train_samples),
                "validation_samples":len(val_samples),"input_shape":[height,width,3],
                "model_foreground":"fracture","history":history.history}
    (output/"training.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
