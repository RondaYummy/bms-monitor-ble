import { Module } from '@nestjs/common';
import { validate } from './env.validation';
import { typeormConfig } from './config/typeorm.config';

import { AppController } from './app.controller';

import { AppService } from './app.service';

import { TelegramModule } from './telegram/telegram.module';
import { ConfigModule } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      validate,
    }),
    TypeOrmModule.forRootAsync(typeormConfig),
    TelegramModule,
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule { }
