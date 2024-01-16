TAG=hw-coordinator

build-local:
	docker buildx build --no-cache -t $(TAG):latest .

build-pi:
#	docker-compose -f pi.yml build
	docker buildx build --platform linux/arm/v7 -t $(TAG):arm . && \
		aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 509080067696.dkr.ecr.us-east-1.amazonaws.com && \
		docker tag $(TAG):arm 509080067696.dkr.ecr.us-east-1.amazonaws.com/$(TAG):latest && \
		docker push 509080067696.dkr.ecr.us-east-1.amazonaws.com/$(TAG):latest


build-pi-nc:
#	docker-compose -f pi.yml build
	docker buildx build --no-cache --platform linux/arm/v7 -t $(TAG):arm . && \
		aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 509080067696.dkr.ecr.us-east-1.amazonaws.com && \
		docker tag $(TAG):arm 509080067696.dkr.ecr.us-east-1.amazonaws.com/$(TAG):latest && \
		docker push 509080067696.dkr.ecr.us-east-1.amazonaws.com/$(TAG):latest

