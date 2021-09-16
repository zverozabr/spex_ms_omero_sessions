import omero
from omero.gateway import BlitzGateway
from os import getenv
from io import BytesIO
import pathlib


try:
    from PIL import Image
except ImportError:
    import Image
# import tempfile


def connect(login, password):
    hostname = getenv('OMERO_HOST')

    conn = BlitzGateway(login, password, host=hostname, secure=True)
    conn.connect()
    conn.c.enableKeepAlive(60)
    print(conn._ic_props)
    img = render_thumbnail('16', conn)
    return conn


def disconnect(conn):
    conn.close()


def print_obj(obj, indent=0):
    res = """%s%s:%s  Name:"%s" (ownerName=%s) (ownerFullName=%s) (ownerType=%s)""" % (
        " " * indent,
        obj.OMERO_CLASS,
        obj.getId(),
        obj.getName(),
        obj.getOwnerOmeName(),
        obj.getOwnerFullName(),
        obj.getOwner())

    return res


def returnObj(obj, indent=0):
    data = {obj.OMERO_CLASS: obj.getId(), 'Name': obj.getName(), 'ownerName': obj.getOwnerOmeName(), 'ownerFullName': obj.getOwnerFullName(),
            'indent': indent}
    return data


def getData():
    conn = connect("root", "omero")
    # my_exp_id = conn.getUser().getId()
    # default_group_id = conn.getEventContext().groupId

    # for dataset in conn.getObjects("Dataset", opts={'owner': my_exp_id,
    #                                                 'group': default_group_id,
    #                                                 'order_by': 'lower(obj.name)',
    #                                                 'limit': 5, 'offset': 0}):
    #     print_obj(dataset)
    #     for project in dataset.listChildren():
    #         print_obj(project, 2)

    image = conn.getObject("Image", "1")

    try:
        # for imageF in dataset.listChildren():
        id = print_obj(image, 4)
        print(id)
        fileset = image.getFileset()       # will be None for pre-FS images
        fs_id = fileset.getId()
        fileset = conn.getObject("Fileset", fs_id)

        for fs_image in fileset.copyImages():
            print(fs_image.getId(), fs_image.getName())
        for orig_file in fileset.listFiles():
            name = orig_file.getName()
            path = orig_file.getPath()

            print(path, name)
            print("Downloading...", name)
            dir = "./data/" + path
            name = dir + name
            pathlib.Path(dir).mkdir(parents=True, exist_ok=True)

            with open(name, "wb") as f:
                for chunk in orig_file.getFileInChunks(buf=2621440):
                    f.write(chunk)
        # image = conn.getObject("Image", id)
        disconnect(conn)
    except AttributeError as ae:
        disconnect(conn)
        raise ae


# getData()

def saveImage(id, conn):
    image = conn.getObject("Image", id)

    try:
        fileset = image.getFileset()
        fs_id = fileset.getId()
        fileset = conn.getObject("Fileset", fs_id)

        for orig_file in fileset.listFiles():
            name = orig_file.getName()
            path = orig_file.getPath()

            print("Downloading...", name)
            dir = "./data/" + path
            name = dir + name
            pathlib.Path(dir).mkdir(parents=True, exist_ok=True)

            with open(name, "wb") as f:
                for chunk in orig_file.getFileInChunks(buf=2621440):
                    f.write(chunk)

        return name
        disconnect(conn)
    except AttributeError as ae:
        disconnect(conn)
        raise ae
    return ''

# conn = connect("localhost", "root", "omero")
# disconnect(conn)


def archived_files(iid=None, conn=None, **kwargs):
    iid = 52
    conn = connect("localhost", "root", "omero")
    """
    Downloads the archived file(s) as a single file or as a zip (if more than
    one file)
    """

    imgIds = [iid]

    images = list()
    wells = list()
    if imgIds:
        images = list(conn.getObjects("Image", imgIds))

    if len(images) == 0:
        message = (
            "Cannot download archived file because Images not "
            "found (ids: %s)" % (imgIds)
        )
        return message

    # Test permissions on images and wheels
    for ob in wells:
        if hasattr(ob, "canDownload"):
            return "HttpResponseNotFound"

    for ob in images:
        well = None
        try:
            well = ob.getParent().getParent()
        except Exception:
            if hasattr(ob, "canDownload"):
                if not ob.canDownload():
                    return "HttpResponseNotFound"
        else:
            if well and isinstance(well, omero.gateway.WellWrapper):
                if hasattr(well, "canDownload"):
                    if not well.canDownload():
                        return "HttpResponseNotFound()"

    # make list of all files, removing duplicates
    fileMap = {}
    for image in images:
        for f in image.getImportedImageFiles():
            fileMap[f.getId()] = f
    files = list(fileMap.values())

    if len(files) == 0:
        message = (
            "Tried downloading archived files from image with no" " files archived."
        )
        return message

    if len(files) == 1:
        orig_file = files[0]
        rsp = orig_file.getFileInChunks(buf=1048576)
        # rsp['conn'] = conn
        # rsp["Content-Length"] = orig_file.getSize()
        # ',' in name causes duplicate headers
        fname = orig_file.getName().replace(" ", "_").replace(",", ".")
        # rsp["Content-Disposition"] = "attachment; filename=%s" % (fname)
        print(fname)
    # rsp["Content-Type"] = "application/force-download"
    rsp.save("/tmp" + fname)


# archived_files()


def render_thumbnail(id, conn, size=96):
    image = conn.getObject("Image", id)
    img_data = image.getThumbnail(size)
    # rendered_thumb = Image.open(BytesIO(img_data))
    return img_data


def is_big_image(conn, image):
    max_w, max_h = conn.getMaxPlaneSize()
    print('Max w, h', max_w, max_h)
    return image.getSizeX() * image.getSizeY() > max_w * max_h


def get_zoom_level_scale(conn, image, region, max_width):
    """Calculate the scale and zoom level we want to use for big image."""
    width = region['width']
    height = region['height']

    zm_levels = image.getZoomLevelScaling()
    # e.g. {0: 1.0, 1: 0.25, 2: 0.0625, 3: 0.03123, 4: 0.01440}
    # Pick zoom such that returned image is below MAX size
    max_level = len(zm_levels.keys()) - 1

    # Maximum size that the rendering engine will render without OOM
    max_plane = conn.getDownloadAsMaxSizeSetting()

    # start big, and go until we reach target size
    zm = 0
    while (zm < max_level and
            zm_levels[zm] * width > max_width or
            zm_levels[zm] * width * zm_levels[zm] * height > max_plane):
        zm = zm + 1

    level = max_level - zm

    # We need to use final rendered jpeg coordinates
    # Convert from original image coordinates by scaling
    scale = zm_levels[zm]
    return scale, level


def render_big_image_region(conn, image, panel, z, t, region, max_width):

    #  Render region of a big image at an appropriate zoom level
    #  so width < max_width

    scale, level = get_zoom_level_scale(conn, image, region, max_width)
    # cache the 'zoom_level_scale', in the panel dict.
    # since we need it for scalebar, and don't want to calculate again
    # since rendering engine will be closed by then
    panel['zoom_level_scale'] = scale

    width = region['width']
    height = region['height']
    x = region['x']
    y = region['y']
    size_x = image.getSizeX()
    size_y = image.getSizeY()
    x = int(x * scale)
    y = int(y * scale)
    width = int(width * scale)
    height = int(height * scale)
    size_x = int(size_x * scale)
    size_y = int(size_y * scale)

    canvas = None
    # Coordinates below are all final jpeg coordinates & sizes
    if x < 0 or y < 0 or (x + width) > size_x or (y + height) > size_y:
        # If we're outside the bounds of the image...
        # Need to render reduced region and paste on to full size image
        canvas = Image.new("RGBA", (width, height), (221, 221, 221))
        paste_x = 0
        paste_y = 0
        if x < 0:
            paste_x = -x
            width = width + x
            x = 0
        if y < 0:
            paste_y = -y
            height = height + y
            y = 0

    # Render the region...
    jpeg_data = image.renderJpegRegion(z, t, x, y, width, height, level=level)
    if jpeg_data is None:
        return

    i = BytesIO(jpeg_data)
    pil_img = Image.open(i)

    # paste to canvas if needed
    if canvas is not None:
        canvas.paste(pil_img, (paste_x, paste_y))
        pil_img = canvas

    return pil_img


def testRenderImage(conn, imageId, width, height):
    try:
        image = conn.getObject("Image", imageId)
        print(image.getName(), image.getDescription())
        # Retrieve information about an image.
        print(" X:", image.getSizeX())
        print(" Y:", image.getSizeY())
        print(" Z:", image.getSizeZ())
        print(" C:", image.getSizeC())
        print(" T:", image.getSizeT())
        # List Channels (loads the Rendering settings to get channel colors)
        for channel in image.getChannels():
            print('Channel:', channel.getLabel())
            print('Color:', channel.getColor().getRGB())
            print('Lookup table:', channel.getLut())
            print('Is reverse intensity?', channel.isReverseIntensity())

        # render the first timepoint, mid Z section
        z = image.getSizeZ() / 2
        t = 0
        viewport_region = {'x': 0, 'y': 0, 'width': width, 'height': height}
        vp_x = viewport_region['x']
        vp_y = viewport_region['y']
        vp_w = viewport_region['width']
        vp_h = viewport_region['height']

        print(is_big_image(conn, image), 'big or not')
        # rendered_image = image.renderImage(z, t)
        max_length = 1.5 * max(vp_w, vp_h)
        extra_w = max_length - vp_w
        extra_h = max_length - vp_h
        viewport_region = {'x': vp_x - (extra_w/2),
                           'y': vp_y - (extra_h/2),
                           'width': vp_w + extra_w,
                           'height': vp_h + extra_h,
                           'zoom_level_scale': 100}
        max_width = vp_w + extra_w
        max_width = max_width * (viewport_region['width'] / vp_w)
        panel = {}
        panel['width'] = 3000
        panel['height'] = 3000

        # image.setGreyscaleRenderingModel()
        size_c = image.getSizeC()
        z = image.getSizeZ() / 2
        t = 0
        for c in range(1, size_c + 1):       # Channel index starts at 1
            channels = [c]                  # Turn on a single channel at a time
            image.setActiveChannels(channels)
            pil_img = render_big_image_region(conn, image, panel, z, t, viewport_region, max_width)
            pil_img.save("./tmp/channels/channel%s.png" % c)

        image.setActiveChannels([0, 1, 2])
        pil_img = render_big_image_region(conn, image, panel, z, t, viewport_region, max_width)
        pil_img.save("./tmp/block.png")

        disconnect(conn)
        return pil_img

    except AttributeError as ae:
        disconnect(conn)
        raise ae


# # test render
# conn = connect('root', 'omero')
# testRenderImage(conn, "52", 300, 300)
