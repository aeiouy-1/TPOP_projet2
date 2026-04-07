%% Configuration de la Red Pitaya (TCP/IP)
IP = '10.68.9.146'; 
port = 5000;
RP = tcpclient(IP, port);
RP.ByteOrder = "big-endian";
configureTerminator(RP, 'CR/LF');

%% Définition de la position constante
voltage_x = 1;
voltage_y = 1;

fprintf('Envoi de la commande de positionnement...\n');

%% NOUVEAU : Envoi des commandes SCPI complètes
% 1. Définir le mode en signal continu (DC)
writeline(RP, 'SOUR1:FUNC DC');
writeline(RP, 'SOUR2:FUNC DC');

% 2. Définir la tension (En mode DC, c'est l'Offset qui définit la tension)
writeline(RP, sprintf('SOUR1:VOLT:OFFS %f', voltage_x));
writeline(RP, sprintf('SOUR2:VOLT:OFFS %f', voltage_y));

% 3. ALLUMER LES SORTIES (C'est la clé !)
writeline(RP, 'OUTPUT1:STATE ON');
writeline(RP, 'OUTPUT2:STATE ON');

fprintf('Miroirs stabilisés à X = %.2f V, Y = %.2f V\n', voltage_x, voltage_y);

%% Maintien de la position
input('Appuie sur Entrée dans cette console quand tu as terminé pour remettre à 0V...', 's');

%% Sécurité : Remise à zéro et fermeture
fprintf('Remise à 0V et extinction des sorties...\n');
writeline(RP, 'SOUR1:VOLT:OFFS 0');
writeline(RP, 'SOUR2:VOLT:OFFS 0');
% Éteindre les sorties
writeline(RP, 'OUTPUT1:STATE OFF');
writeline(RP, 'OUTPUT2:STATE OFF');

clear RP;
fprintf('Connexion fermée avec succès.\n');