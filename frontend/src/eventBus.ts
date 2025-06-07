import mitt from 'mitt';

type Events = {
  'session:remove': string;
};

export const eventBus = mitt<Events>();
