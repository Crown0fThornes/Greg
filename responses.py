from command_handler import Context
import time;

class ResponseRequest():
    
    active_requests = [];
    
    def __init__(self, return_func, name, type, activation_context, response_context, key = None, timeout = None, **values):
        self.return_func = return_func;
        self.name = name;
        self.type = type;
        self.activation_context = activation_context;
        self.response_context = response_context;
        self.key = key;
        self.values = values;
        self.expiration = time.time() + (600 if timeout is None else timeout);
        self.met = False;
        ResponseRequest.active_requests.append(self);
    
    async def fulfill_message_requests(message, context: Context, neighbor):
        to_respond = [];
        to_not_respond = [];
        to_remove = [];
        for request in ResponseRequest.active_requests:
            if time.time() > request.expiration:
                to_remove.append(request);
                continue;
            if request.type != "MESSAGE":
                to_not_respond.append(request);
                continue;
            if context == request.activation_context:
                if request.key is None:
                    to_respond.append(request);
                    continue;
                if request.key(context):
                    to_respond.append(request);
                    continue;
                else:
                    to_not_respond.append(request);
                    continue;
            else:
                to_not_respond.append(request)
                    
        ResponseRequest.active_requests = to_not_respond;
        
        for request in to_respond:
            await request.return_func(neighbor, request.activation_context, ResponsePackage(request, message.content));
        
    async def fulfill_reaction_requests(reaction, context: Context, neighbor):
        to_respond = [];
        to_not_respond = [];
        to_remove = [];
        for request in ResponseRequest.active_requests:
            print(request);
            if time.time() > request.expiration:
                to_remove.append(request);
                print("Timed out!");
                continue;
            if request.type != "REACTION":
                to_not_respond.append(request);
                print("Wrong type");
                continue;
            if context == request.activation_context:
                if request.key is None:
                    to_respond.append(request);
                    continue;
                if request.key(context):
                    to_respond.append(request);
                    continue;
                else:
                    to_not_respond.append(request);
                    print("Failed key");
                    continue;
            else:
                to_not_respond.append(request)
            print("Wrong context!");
                    
        ResponseRequest.active_requests = to_not_respond;
        
        for request in to_respond:
            await request.return_func(neighbor, request.activation_context, ResponsePackage(request, reaction.emoji));
        
class ResponsePackage():
    def __init__(self, request, content): 
        self.name = request.name;
        self.type = request.type;
        self.activation_context = request.activation_context;
        self.response_context = request.response_context;
        self.key = request.key;
        self.values = request.values;
        self.content = content
        