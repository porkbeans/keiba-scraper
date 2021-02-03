.PONY: build push

build:
	docker build -t porkbeans/keiba-scraper:latest .

push: build
	docker push porkbeans/keiba-scraper:latest
