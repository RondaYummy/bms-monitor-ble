<template>
  <div class="text">Отримання даних...</div>
  <div class="box">
    <div class="comp"></div>
    <div class="loader"></div>
    <div class="con"></div>
    <div class="byte"></div>
    <div class="server"></div>
  </div>
</template>

<script setup lang="ts"></script>

<style scoped lang="scss">
.box {
  width: 240px;
  height: 150px;
  position: absolute;
  top: calc(50% - 25px);
  top: -webkit-calc(50% - 25px);
  left: calc(50% - 120px);
  left: -webkit-calc(50% - 120px);
}

.text {
  font-family: 'Lato', sans-serif;
  color: #fff;
  font-weight: 300;
  font-size: 30px;
  position: absolute;
  top: calc(50% - 105px);
  top: -webkit-calc(50% - 105px);
  left: calc(50% - 160px);
  left: -webkit-calc(50% - 135px);
  opacity: 1;
  -webkit-animation: fade-in-out 2.5s infinite;
  -moz-animation: fade-in-out 2.5s infinite;
  -o-animation: fade-in-out 2.5s infinite;
  animation: fade-in-out 2.5s infinite;
}

.comp {
  position: absolute;
  top: 0px;
  width: 80px;
  height: 55px;
  border: 3px solid #fff;
  border-radius: 5px;
}

.comp:after {
  content: '';
  position: absolute;
  z-index: 5;
  top: 19px;
  left: 5px;
  width: 65px;
  height: 10px;
  border-radius: 360px;
  border: 3px solid #fff;
}

.loader {
  position: absolute;
  z-index: 5;
  top: 23px;
  left: 10px;
  width: 8px;
  height: 8px;
  border-radius: 360px;
  background: #fff;
  -webkit-animation: loader 5s infinite linear 0.5s;
  -moz-animation: loader 5s infinite linear 0.5s;
  -o-animation: loader 5s infinite linear 0.5s;
  animation: loader 5s infinite linear 0.5s;
}

.con {
  position: absolute;
  top: 28px;
  left: 85px;
  width: 100px;
  height: 3px;
  background: #fff;
}

.byte {
  position: absolute;
  top: 25px;
  left: 80px;
  height: 9px;
  width: 9px;
  background: #fff;
  border-radius: 360px;
  z-index: 6;
  opacity: 0;
  -webkit-animation: byte_animate 5s infinite linear 0.5s;
  -moz-animation: byte_animate 5s infinite linear 0.5s;
  -o-animation: byte_animate 5s infinite linear 0.5s;
  animation: byte_animate 5s infinite linear 0.5s;
}

.server {
  position: absolute;
  top: 22px;
  left: 185px;
  width: 35px;
  height: 35px;
  z-index: 1;
  border: 3px solid #fff;
  background: #459bf9;
  border-radius: 360px;
  -webkit-transform: rotateX(58deg);
  -moz-transform: rotateX(58deg);
  -o-transform: rotateX(58deg);
  transform: rotateX(58deg);
}

.server:before {
  content: '';
  position: absolute;
  top: -47px;
  left: -3px;
  width: 35px;
  height: 35px;
  z-index: 20;
  border: 3px solid #fff;
  background: #459bf9;
  border-radius: 360px;
}

.server:after {
  position: absolute;
  top: -26px;
  left: -3px;
  border-left: 3px solid #fff;
  border-right: 3px solid #fff;
  width: 35px;
  height: 40px;
  z-index: 17;
  background: #459bf9;
  content: '';
}

/*Byte Animation*/
@-webkit-keyframes byte_animate {
  0% {
    opacity: 0;
    left: 80px;
  }

  4% {
    opacity: 1;
  }

  46% {
    opacity: 1;
  }

  50% {
    opacity: 0;
    left: 185px;
  }

  54% {
    opacity: 1;
  }

  96% {
    opacity: 1;
  }

  100% {
    opacity: 0;
    left: 80px;
  }
}

@-moz-keyframes byte_animate {
  0% {
    opacity: 0;
    left: 80px;
  }

  4% {
    opacity: 1;
  }

  46% {
    opacity: 1;
  }

  50% {
    opacity: 0;
    left: 185px;
  }

  54% {
    opacity: 1;
  }

  96% {
    opacity: 1;
  }

  100% {
    opacity: 0;
    left: 80px;
  }
}

@-o-keyframes byte_animate {
  0% {
    opacity: 0;
    left: 80px;
  }

  4% {
    opacity: 1;
  }

  46% {
    opacity: 1;
  }

  50% {
    opacity: 0;
    left: 185px;
  }

  54% {
    opacity: 1;
  }

  96% {
    opacity: 1;
  }

  100% {
    opacity: 0;
    left: 80px;
  }
}

@keyframes byte_animate {
  0% {
    opacity: 0;
    left: 80px;
  }

  4% {
    opacity: 1;
  }

  46% {
    opacity: 1;
  }

  50% {
    opacity: 0;
    left: 185px;
  }

  54% {
    opacity: 1;
  }

  96% {
    opacity: 1;
  }

  100% {
    opacity: 0;
    left: 80px;
  }
}

/*LOADER*/
@-webkit-keyframes loader {
  0% {
    width: 8px;
  }

  100% {
    width: 63px;
  }
}

@-moz-keyframes loader {
  0% {
    width: 8px;
  }

  100% {
    width: 63px;
  }
}

@-o-keyframes loader {
  0% {
    width: 8px;
  }

  100% {
    width: 63px;
  }
}

@keyframes loader {
  0% {
    width: 8px;
  }

  100% {
    width: 63px;
  }
}

/*FADE IN-OUT*/
@-webkit-keyframes fade-in-out {
  0% {
    opacity: 1;
  }

  50% {
    opacity: 0;
  }

  100% {
    opacity: 1;
  }
}

@-moz-keyframes fade-in-out {
  0% {
    opacity: 1;
  }

  50% {
    opacity: 0;
  }

  100% {
    opacity: 1;
  }
}

@-o-keyframes fade-in-out {
  0% {
    opacity: 1;
  }

  50% {
    opacity: 0;
  }

  100% {
    opacity: 1;
  }
}

@keyframes fade-in-out {
  0% {
    opacity: 1;
  }

  50% {
    opacity: 0;
  }

  100% {
    opacity: 1;
  }
}
</style>
