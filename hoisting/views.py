from PIL import Image as PIL
from django.contrib import messages
from django.core.files.images import get_image_dimensions
from django.db import IntegrityError
from django.http import HttpResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from ipware import get_client_ip

from .forms import ImageForm
from .models import Image
from .models import Vote


def save_image(request):
    saved = False
    image = None
    if request.method == "POST":
        image_form = ImageForm(request.POST, request.FILES)

        if image_form.is_valid():
            image = Image()
            image.photo = image_form.cleaned_data["photo"]
            width, height = get_image_dimensions(image.photo)
            image.width = width
            image.length = height
            image.private = image_form.cleaned_data['private'] or False
            image.save()
            saved = True

    return render(request, 'saved.html', {'saved': saved, 'id': image.pk if image else None})


def get_image_by_resolution(request, width, height):
    """
    Find all the images in the database with this width x height and choose one of those images, and render that image
    """

    # First try to find an image with the exact resolution, and choose the earliest one
    image = Image.objects.filter(width=width, length=height).order_by('uploaded_at').first()

    # If there is no image with the exact resolution, find the image with closest resolution
    if not image:
        # Order the image by area difference of the stored image compared to input resolution
        image = Image.objects.all().extra(select={'pixels': 'abs(width - %s) * abs(length - %s)'},
                                          select_params=(int(width), int(height))).order_by('pixels').first()

        # If an image exists, resize and render the image as PNG
        if not image:
            raise Http404()
        else:
            resized = PIL.open(image.photo).resize((int(width), int(height)), PIL.LANCZOS)
            response = HttpResponse(content_type="image/png")
            resized.save(response, "PNG")
            return response
    else:
        return HttpResponse(image.photo, content_type='image/jpeg')


def get_image_by_id(request, id):
    """
    Find an image with this ID in the database and return the image, otherwise 404
    """
    image = get_object_or_404(Image, pk=id)
    return HttpResponse(image.photo, content_type='image/jpeg')


def add_vote(request, id):
    if request.method == "POST":
        image = get_object_or_404(Image, pk=id)

        ip, is_routable = get_client_ip(request)

        vote = Vote()
        vote.image_vote = image
        vote.ip = ip
        try:
            vote.save()
        except IntegrityError:
            messages.error(request, 'You already voted for this.')
        return redirect("/")
