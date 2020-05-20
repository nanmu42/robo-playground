# Measure Distance

## Actual Size Known

Per Pinhole camera model, we have:

`actual size` / `size on camera sensor` = `distance` / `focal length`

thus,

`distance` = `focal length` * `actual size` / `size on camera sensor`

if we need `focal length`:

`focal length` = `distance` * `size on camera sensor` / `actual size`

## Actual Size Unknown

The distance can be calculated under limited circumstance, where the object and robot are both at the same height(measure from bottoms).

A right triangle consisting of the camera, robot bottom and object bottom are established. The camera height, which is a known value, is one right angele edge and the corner degree between the camera height and the hypotenuse can be obtained by robot gimbal status and computer vision.

## References

* https://en.wikipedia.org/wiki/Pinhole_camera_model