var app = {
    init: function() {
        var self = this;
        // sometimes i want to change the hash and don't want the hash change event to execute
        this.ignoreHashChange = 0;
        // holds the progress bar timing interval
        this.tick = null;
        // hold timing interval for rebuilding playlist
        this.queuePlaylistTick = null;
        // number of requests to rebuilt playlist
        // this is used to determine if we should ignore ajax responses
        this.numRebuildPlaylistRequests = 0;
        // record ID from datatable record set of current song
        this.currentSong = null;
        this.currentSongId = null;
        this.currentSearch = null;
        // copy of original data returned from last search request
        // shuffle always needs to occur on original data
        this.originalData = null;

        // UI
        this.progressbar = $('.progressbar');
        this.btnPlay = $('.btnPlay');
        this.btnPause = $('.btnPause');
        this.btnPrevious = $('.btnPrevious');
        this.btnNext = $('.btnNext');
        this.btnShuffle = $('.btnShuffle');
        this.player = document.getElementById('player');
        this.playerHolder = $('#player-holder');
        this.preloadNotice = $('.preloadNotice');
        this.search = $('#s');
        this.searchLoading = $('.search-loading');

        this.setupAudioControls();
        this.setupInventory();
        this.setupPlaylist();

        $(window).bind('hashchange', function(e) {
            if (self.ignoreHashChange > 0) {
                self.ignoreHashChange--;
                return;
            }
            self.locationChanged();
        });

        var qs = this.parseHash();
        if (qs) {
            this.currentSongId = qs.s;
            this.search.val(qs.q);
            this.locationChanged();
            $("#tabs").tabs().tabs('select', 1);
        } else {
            $("#tabs").tabs().tabs('select', 0);
        }
    },
    setupAudioControls: function() {
        var self = this;
        this.progressbar.progressbar({value: 0});
        this.progressbar.click(function(e) {
            self.updateProgress(e);
        });
        this.btnPlay.click(function(e) {
            e.preventDefault();
            self.play();
        });
        this.btnPause.click(function(e) {
            e.preventDefault();
            self.pause();
        });
        this.btnPrevious.click(function(e) {
            e.preventDefault();
            self.gotoPreviousSong();
        });
        this.btnNext.click(function(e) {
            e.preventDefault();
            self.gotoNextSong();
        });
        this.btnShuffle.click(function(e) {
            e.preventDefault();
            self.shuffle();
        });
    },
    setupInventory: function() {
        var self = this;
        var artistFormatter = function(elCell, oRecord, oColumn, oData) {
            elCell.innerHTML += '<a href="#" class="searchable">' + oData + '</a>';
        };
        var albumFormatter = function(elCell, oRecord, oColumn, oData) {
            var mid = Math.round(oData.length / 2);
            var str = '<table class="album-table"><tr><td>';
            $.each(oData, function(i, obj) {
                if (i > 0 && i % mid == 0) {
                    str += '</td><td>';
                }
                str += '<p><a href="#" class="searchable">' + obj.name + '</a></p>';
            });
            str += '</td></tr></table>';
            elCell.innerHTML = str;
        };
        var columns = [
            {key: 'name', label: 'Artist', formatter: artistFormatter},
            {key: 'albums', label: 'Albums', formatter: albumFormatter}
        ];
        this.dsArtists = new YAHOO.util.DataSource('inventory.json');
        this.dsArtists.responseType = YAHOO.util.DataSource.TYPE_JSON;
        this.dsArtists.responseSchema = {
            resultsList: 'result',
            fields: ['name', 'albums']
        };

        this.dtArtists = new YAHOO.widget.DataTable("albums-table", columns, this.dsArtists, null);

        $('.searchable').live('click', function(e) {
            e.preventDefault();
            self.addToPlaylist('"' + $(this).text() + '"');
            var pos = $(this).position();
            var a = $(this).clone();
            a.css('position', 'absolute');
            a.css('top', (pos.top + 110) + 'px');
            a.css('left', pos.left + 'px');
            a.appendTo($('body'));
            a.animate({top: 80 + $(window).scrollTop(), left: 85}, 500, 'swing', function() {
                a.remove();
            });
        });
    },
    setupPlaylist: function() {
        var self = this;

        var columns = [
            {key: 'artist', label: 'Artist', sortable:true},
            {key: 'album', label: 'Album', sortable:true},
            {key: 'title', label: 'Title', sortable:true},
            {key: 'track', label: 'Track', sortable:true}
        ];

        this.myDataSource = new YAHOO.util.DataSource();
        this.myDataSource.responseType = YAHOO.util.DataSource.JSON_ARRAY;
        this.myDataSource.responseSchema = {
            fields: ['name']
        };

        this.myDataTable = new YAHOO.widget.DataTable("songs-table", columns, this.myDataSource, {selectionMode:'single', initialLoad: false});
        this.myDataTable.subscribe("rowMouseoverEvent", this.myDataTable.onEventHighlightRow);
        this.myDataTable.subscribe("rowMouseoutEvent", this.myDataTable.onEventUnhighlightRow);
        this.myDataTable.subscribe("rowClickEvent", this.myDataTable.onEventSelectRow);
        this.myDataTable.subscribe("rowClickEvent", function(e) {
            var rid = self.myDataTable.getSelectedRows()[0];
            var rs = self.myDataTable.getRecordSet();
            var r = rs.getRecord(rid);
            self.currentSong = rs.getRecordIndex(r);
            self.currentSongId = r.getData('id');
            self.queueNextSong(self.currentSongId);
        });

        this.search.keyup(function(e) {
            self.queueRebuildPlaylist(self.search.val());
        });
    },
    parseHash: function() {
        if (window.location.hash.length < 1) {
            return false;
        }
        var hash = window.location.hash.substr(1);
        var parts = hash.split(',');
        var q = null;
        var s = null;
        $.each(parts, function(i, part) {
            if (part.indexOf('q=') != -1) {
                q = part.substr(2);
            } else if (part.indexOf('s=') != -1) {
                s = part.substr(2);
            }
        });
        return {q: q, s: s};
    },
    locationChanged: function() {
        var self = this;
        var info = this.parseHash();
        if (!info) {
            return;
        }
        var q = info.q;
        var s = info.s;
        if (q == self.currentSearch) {
            q = null;
        }
        if (q) {
            self.queueRebuildPlaylist(q, function() {
                if (s) {
                    self.queueNextSong(s);
                }
            });
        } else if (s) {
            self.queueNextSong(s);
        }
    },
    updateProgressBarUI: function() {
        var currentTime = this.getCurrentTime();
        var duration = this.getDuration();
        if (duration <= 0) {
            return;
        }
        if (currentTime >= duration) {
            this.pause();
            this.gotoNextSong();
            return;
        }
        var value = currentTime / duration * 100;
        $('.progressbar').progressbar('option', 'value', value);
    },
    updateProgress: function(evt) {
        var bar = $(evt.currentTarget);
        var mouseX = evt.pageX;
        if (Math.min(bar.width(), mouseX) <= 0) {
            return;
        }
        var perc = (mouseX - bar.offset().left) / bar.width();
        var targetSec = this.getDuration() * perc;
        this.seekTo(targetSec);
        this.play();
        this.updateProgressBarUI();
    },
    play: function() {
        var self = this;
        // there is no song selected to play
        if (this.currentSong == null) {
            this.loadInitialSong();
            return;
        }
        this.btnPlay.addClass('hide');
        this.btnPause.removeClass('hide');
        this.player.play();
        clearInterval(this.tick);
        this.tick = setInterval(function() {
            self.updateProgressBarUI();
        }, 500);
    },
    pause: function() {
        this.btnPlay.removeClass('hide');
        this.btnPause.addClass('hide');
        this.player.pause();
        clearInterval(this.tick);
    },
    shuffle: function() {
        var dt = this.myDataTable;
        var rs = dt.getRecordSet();
        var len = rs.getLength();
        if (len == 0) {
            return;
        }
        var data = this.originalData.slice();
        var shuffledData = [];
        for(var i = 0; i < len; i++) {
            var r = Math.random();
            var k = Math.round(r * (len - i - 1));
            shuffledData.push(data.splice(k, 1)[0]);
        }
        dt.deleteRows(0, len);
        dt.addRows(shuffledData);
        this.highlightSong(this.currentSongId);
        this.setWindowHash(this.currentSearch, this.currentSongId);
    },
    seekTo: function(seconds) {
        this.player.currentTime = seconds;
    },
    getCurrentTime: function() {
        return this.player.currentTime;
    },
    getDuration: function() {
        return this.player.duration;
    },
    // Selects the first song in the playlist.
    // Triggered when Play button is pressed before a song is selected.
    loadInitialSong: function() {
        var dt = this.myDataTable;
        var rs = dt.getRecordSet();
        if (rs.getLength() == 0) {
            return;
        }
        var r = rs.getRecord(0);
        this.queueNextSong(r.getData('id'));
    },
    showPreloadNotice: function(msg) {
        this.preloadNotice.show();
        this.preloadNotice.text(msg);
    },
    hidePreloadNotice: function() {
        this.preloadNotice.hide();
    },
    gotoPreviousSong: function() {
        var dt = this.myDataTable;
        var rs = dt.getRecordSet();
        if (rs.getLength() == 0) {
            return;
        }
        var prevSongID = this.currentSong - 1 < 0 ? rs.getLength() - 1 : this.currentSong - 1;
        var prevSong = rs.getRecord(prevSongID);
        this.queueNextSong(prevSong.getData('id'));
    },
    gotoNextSong: function() {
        var dt = this.myDataTable;
        var rs = dt.getRecordSet();
        if (rs.getLength() == 0) {
            return;
        }
        var nextSongID = (this.currentSong + 1) % rs.getLength();
        var nextSong = rs.getRecord(nextSongID);
        this.queueNextSong(nextSong.getData('id'));
    },
    getRecordInfoFromId: function(id) {
        var dt = this.myDataTable;
        var rs = dt.getRecordSet();
        var len = rs.getLength();
        for(var i = 0; i < len; i++) {
            var r = rs.getRecord(i);
            if (r.getData('id') == id) {
                return {index: i, record: r};
            }
        }
        return null;
    },
    addToPlaylist: function(str) {
        var oldVal = this.search.val();
        if (oldVal.length > 0) {
            oldVal += ' ';
        }
        oldVal += str;
        this.search.val(oldVal);
        this.queueRebuildPlaylist(oldVal);
    },
    queueRebuildPlaylist: function(val, cb) {
        var self = this;
        clearTimeout(this.queuePlaylistTick);
        this.queuePlaylistTick = setTimeout(function() {
            self.rebuildPlaylist(val, cb);
        }, 1000);
    },
    queueNextSong: function(id) {
        var self = this;
        var dt = this.myDataTable;
        if (!this.songExistsInPlaylist(id)) {
            return;
        }
        this.showPreloadNotice('Loading next song...');
        var nextSong = document.createElement('audio');
        nextSong.autoplay = 'autoplay';
        nextSong.preload = 'auto';
        nextSong.src = 'download/' + id + '.mp3';
        nextSong.id = 'player';
        $(nextSong).bind('error', function(data) {
            self.showPreloadNotice('ERROR: Could not load file');
            self.preloadNotice.effect('shake', {times: 4}, 55);
        });
        $(nextSong).bind('loadeddata', function() {
            self.loadAlbumArt(id);
            self.setWindowHash(self.currentSearch, id);
            self.highlightSong(id);
            self.hidePreloadNotice();
            $(self.player).remove();
            self.player = nextSong;
            self.playerHolder.append(nextSong);
            self.play();
        });
    },
    rebuildPlaylist: function(query, callback) {
        var self = this;
        this.numRebuildPlaylistRequests++;
        var thisRequest = this.numRebuildPlaylistRequests;
        this.searchLoading.show();
        $.get('search.json', {q: query}, function(data) {
            if (self.numRebuildPlaylistRequests > thisRequest) {
                return;
            }
            self.originalData = data.result;
            self.searchLoading.hide();
            self.currentSearch = query;
            var dt = self.myDataTable;
            dt.deleteRows(0, dt.getRecordSet().getLength());
            dt.addRows(data.result);
            if (self.songExistsInPlaylist(self.currentSongId)) {
                self.highlightSong(self.currentSongId);
            } else {
                self.currentSong = null;
                self.currentSongId = null;
            }
            self.setWindowHash(query, self.currentSongId);
            self.search.val(query);
            if (data.length == 0) {
                dt.showTableMessage(YAHOO.widget.DataTable.MSG_ERROR, YAHOO.widget.DataTable.CLASS_ERROR);
            }
            if (callback) {
                callback();
            }
        });
    },
    songExistsInPlaylist: function(id) {
        return this.getRecordInfoFromId(id) != null;
    },
    highlightSong: function(id) {
        if (id == null) {
            return;
        }
        var info = this.getRecordInfoFromId(id);
        this.currentSong = info.index;
        this.currentSongId = id;
        document.title = info.record.getData('name');
        var dt = this.myDataTable;
        dt.unselectAllRows();
        dt.selectRow(this.currentSong);
        // position of song row in table - 25 (#songs-table margin-top)
        $(window).scrollTop($(dt.getTrEl(this.currentSong)).position().top - 45);
    },
    //@q playlist query
    //@s current song
    setWindowHash: function(q, s) {
        var parts = [];
        if (q != null) {
            parts.push('q=' + q);
        }
        if (s != null) {
            parts.push('s=' + s);
        }
        var newHash = parts.join(',');
        var oldHash = window.location.hash;
        oldHash = oldHash.length > 1 ? oldHash.substr(1) : oldHash;
        if (oldHash != newHash) {
            this.ignoreHashChange++;
        }
        window.location.hash = newHash;
    },
    loadAlbumArt: function(id) {
        $.get('art/' + id + '.json', function(data) {
            if (data && data.items && data.items.length > 0) {
                var n = Math.floor(Math.random() * data.items.length);
                var imgUrl = data.items[n].link;
                $('#player-holder').css({backgroundImage: 'url(' + imgUrl + ')'});
            }
        });
    }
};
