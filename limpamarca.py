#!/usr/bin/python
# -*- coding: utf-8 -*-
# Data: 13/09/2022

import cv2
import numpy as np
from pdf2image import convert_from_path
from PIL import Image

def back_rm(filename):
    # Carrega a imagem
    img = cv2.imread(filename)

    # Converte para cinza
    gr = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Faz uma cópia da imagem cinza
    bg = gr.copy()

    # Transformação morfológica
    for i in range(5):
        kernel2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                            (2 * i + 1, 2 * i + 1))
        bg = cv2.morphologyEx(bg, cv2.MORPH_CLOSE, kernel2)
        bg = cv2.morphologyEx(bg, cv2.MORPH_OPEN, kernel2)

    # Subtrai a imagem cinza da cópia processada
    dif = cv2.subtract(bg, gr)

    # Aplicando limites
    bw = cv2.threshold(dif, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    dark = cv2.threshold(bg, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    # Extrai pixels na região escura
    darkpix = gr[np.where(dark > 0)]

    # Aplica limites na região escura para pegar o pixel mais escuros dessa região
    darkpix = cv2.threshold(darkpix, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    # Cola os pixels extraídos na região da marca d'água
    bw[np.where(dark > 0)] = darkpix.T

    cv2.imwrite('rm_'+filename, bw)

def convimage(imput, mark):
    def areaFilter(minArea, inputImage):

        componentsNumber, labeledImage, componentStats, componentCentroids = \
        cv2.connectedComponentsWithStats(inputImage, connectivity=4)

        remainingComponentLabels = [i for i in range(1, componentsNumber) if componentStats[i][4] >= minArea]

        filteredImage = np.where(np.isin(labeledImage, remainingComponentLabels) == True, 255, 0).astype('uint8')

        return filteredImage

    # Lê imagem
    img = cv2.imread(imput)

    # Armazena uma cópia para usar no inpaint
    originalImg = img.copy()

    # Converte para float e divide por 255:
    imgFloat = img.astype(np.float64) / 255.

    # Calcula o canal K:
    kChannel = 1 - np.max(imgFloat, axis=2)

    # Aplica os ajustes de brilho e contraste no canal K
    alpha = 0
    beta = 1.2
    adjustedK = cv2.normalize(kChannel, None, alpha, beta, cv2.NORM_MINMAX, cv2.CV_32F)

    # Converte de volta para uint 8:
    adjustedK = (255*adjustedK).astype(np.uint8)

    # Limite adaptatido de ajuste do canal K:
    windowSize = 21
    windowConstant = 11
    binaryImg = cv2.adaptiveThreshold(adjustedK, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, windowSize, windowConstant)

    # Obtém as maiores bolhas da imagem:
    minArea = 180
    bigBlobs = areaFilter(minArea, binaryImg)

    # Obtém as menores bolhas da imagem:
    minArea = 20
    smallBlobs = areaFilter(minArea, binaryImg)

    # Isolando a marca:
    #textMask = smallBlobs - bigBlobs
    textMask = cv2.imread(mark)
    maskImg = textMask.copy()
    maskFloat = maskImg.astype(np.float64) / 255.
    kChannel = 1 - np.max(maskFloat, axis=2)
    adjustedK = cv2.normalize(kChannel, None, alpha, beta, cv2.NORM_MINMAX, cv2.CV_32F)
    adjustedK = (255*adjustedK).astype(np.uint8)
    textMask = cv2.adaptiveThreshold(adjustedK, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, windowSize, windowConstant)

    #Borra a máscara para obter uma melhor cobertura.
    kernelSize = (3, 3)
    textMask = cv2.GaussianBlur(textMask, kernelSize, cv2.BORDER_DEFAULT)

    #Aplica o método inpaint:
    inpaintRadius = 10
    inpaintMethod = cv2.INPAINT_TELEA
    result = cv2.inpaint(originalImg, textMask, inpaintRadius, inpaintMethod)
    cv2.imwrite('conv'+imput, result)

def salvar(i):
    # Parâmetros (numéro de páginas do PDF - 1 e formato do nome das fotos
    min_range = 0
    max_range = i
    global prefix
    suffix = ".jpg"
    images = []

    images = []
    for i in range(min_range, max_range + 1):
        fname = prefix + str(i) + suffix
        print(fname)
        # Carrega a imagem
        im = Image.open(fname)
        # Converte para RGB se a imagem for do tipo RGBA
        if im.mode == "RGBA":
            im = im.convert("RGB")
        # Adiciona a imagem na lista
        images.append(im)

    # Compila todas as imagens em um PDF único
    images[0].save("final.pdf", save_all = True, append_images = images[1:])

original = input("Digite o nome do arquivo junto com a extensão. Ex.: original.pdf\n")
print("Extraindo...")
# Armazenar as imagens com base no PDF - necessida do poppler (https://github.com/oschwartz10612/poppler-windows/releases/)
images = convert_from_path(original, poppler_path = r"poppler-22.04.0\Library\bin")

#Percorre as páginas e salva uma a uma com o nome em ordem
for i in range(len(images)):
    images[i].save('page'+ str(i) +'.jpg', 'JPEG')
    print(i*".")
    
opt = int(input("\nDigite 1 para método borrado (necessita da máscara salva como marca.jpg) \nDigite 2 para método preto e branco \n"))

if opt == 1:
    prefix = "convpage" #prefixo para o nome de imagem intermediario antes de converter
    for i in range(len(images)):
        convimage('page'+str(i)+'.jpg', 'marca.jpg')
        print("Convertido",i)
else:
    if opt == 2:
        prefix = "rm_page"
        for i in range(len(images)):
            back_rm('page'+str(i)+'.jpg')
            print("Convertido",i)
    else:
        print("Erro. Tente novamente.")
salvar(len(images)-1)
print("\nConcluído!\n")
